from django.shortcuts import get_object_or_404, render
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ViewSet

from .mixins import ModelViewMixin
from .models import Cart, CartItems, Product
from .serializers import CartItemSerializer, CartSerializer, ProductListSerializer, ProductSerializer


class ProductViewSet(ModelViewMixin, ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    serializer_action_classes = {
        "list": ProductListSerializer,
        "create": ProductSerializer,
        "retrieve": ProductSerializer,
    }

    @action(methods=["GET"], detail=False)
    def search(self, request):
        products = self.queryset
        category_id = request.query_params.get("category_id", None)
        name = request.query_params.get("name", None)
        if category_id:
            products = products.filter(category_id=category_id)
        if name:
            products = products.filter(name__icontains=name)

        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CartViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    #queryset = Cart.objects.all()
    serializer_class = CartSerializer
    serializer_action_classes = {"retrieve": CartSerializer}

    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user)

    def retrieve(self, request, pk=None, *args, **kwargs):
        cart = get_object_or_404(self.get_queryset(), pk=pk)
        prod_quant_dct = {}
        print(cart)
        for i in CartSerializer(cart).data["items"]:
            if i["quantity"] > i["product_available_quantity"]:
                prod_quant_dct.setdefault(i['product_id'], i["product_available_quantity"])

        for product in prod_quant_dct:
            cart_item = CartItems.objects.get(cart=cart, product=product)
            cart_item.quantity = prod_quant_dct[product]
            cart_item.save()
        serializer = CartSerializer(cart)
        return Response(serializer.data)

    def find_cart(self, cart_id: str, product_id: str):
        cart = get_object_or_404(self.queryset, pk=cart_id)
        product = get_object_or_404(Product, pk=product_id)
        return cart, product

    @staticmethod
    def validate_quantity(requested_quantity: int, cart, product, **kwargs):
        cart_item = CartItems.objects.get(cart=cart, product=product)
        product_available_quantity = product.available_quantity

        match requested_quantity:

            case requested_quantity if requested_quantity < 0:
                return Response({"error": "Invalid quantity"}, status=status.HTTP_400_BAD_REQUEST)

            case _:
                if cart_item.quantity > product_available_quantity:
                    cart_item.quantity = product_available_quantity
                    cart_item.save()
                else:
                    cart_item.save()

        return Response(CartSerializer(cart).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["POST", "PATCH", "DELETE"])
    def item(self, request):
        cart, product = self.find_cart(request.data.get("cart_id"), request.data.get("product_id"))

        match request.method:

            case "POST":
                try:
                    return self.validate_quantity(
                        requested_quantity=request.data.get("quantity"), cart=cart, product=product
                    )
                except CartItems.DoesNotExist:
                    CartItems.objects.create(cart=cart, product=product, quantity=1)
                    return self.validate_quantity(requested_quantity=request.data.get("quantity"), cart=cart, product=product)

            case "PATCH":
                return self.validate_quantity(
                    requested_quantity=request.data.get("quantity"), cart=cart, product=product
                )

            case "DELETE":
                try:
                    CartItems.objects.filter(cart=cart, product=product).delete()
                    return Response(CartSerializer(cart).data, status=status.HTTP_200_OK)
                except CartItems.DoesNotExist:
                    return Response(CartSerializer(cart).data, status=status.HTTP_204_NO_CONTENT)
