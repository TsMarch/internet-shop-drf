from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from .mixins import ModelViewMixin
from .models import Cart, CartItems, Product, Order, OrderItems
from .serializers import CartSerializer, ProductListSerializer, ProductSerializer, OrderSerializer, CartItemSerializer


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
    serializer_class = CartSerializer

    def get_queryset(self):
        user_cart, _ = Cart.objects.get_or_create(user=self.request.user)
        return user_cart

    def list(self, request, *args, **kwargs):
        cart = self.get_queryset()
        serializer = CartSerializer(cart)
        return Response(serializer.data)

    def retrieve(self, request, pk=None, *args, **kwargs):
        cart = self.get_queryset()
        prod_quant_dct = {}
        for i in CartSerializer(cart).data["items"]:
            if i["quantity"] > i["product_available_quantity"]:
                prod_quant_dct.setdefault(i["product_id"], i["product_available_quantity"])

        for product in prod_quant_dct:
            cart_item = CartItems.objects.get(cart=cart, product=product)
            cart_item.quantity = prod_quant_dct[product]
            cart_item.save()
        serializer = CartSerializer(cart)
        return Response(serializer.data)

    def find_cart(self, product_id: str):
        cart = self.get_queryset()
        product = get_object_or_404(Product, pk=product_id)
        return cart, product

    @staticmethod
    def validate_quantity(requested_quantity: int, cart, product, **kwargs):
        cart_item = CartItems.objects.get(cart=cart, product=product)

        match requested_quantity:

            case requested_quantity if requested_quantity < 0:
                return Response({"error": "Invalid quantity"}, status=status.HTTP_400_BAD_REQUEST)

            case _:
                cart_item.price = product.price
                cart_item.save()
                if cart_item.quantity > product.available_quantity:
                    cart_item.quantity = product.available_quantity
                    cart_item.save()
                else:
                    cart_item.save()

        return Response(CartSerializer(cart).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["POST", "PATCH", "DELETE"])
    def item(self, request):
        cart, product = self.find_cart(product_id=request.data.get("product_id"))
        match request.method:

            case "POST":
                try:
                    return self.validate_quantity(
                        requested_quantity=request.data.get("quantity"), cart=cart, product=product
                    )
                except CartItems.DoesNotExist:
                    CartItems.objects.create(cart=cart, product=product, quantity=1)
                    return self.validate_quantity(
                        requested_quantity=request.data.get("quantity"), cart=cart, product=product
                    )

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


class OrderViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderSerializer
    serializer_action_classes = {"retrieve": OrderSerializer}

    def get_queryset(self, **kwargs):
        if not kwargs: return Order.objects.filter(user=self.request.user)
        match kwargs.get('action', None):
            case 'create':
                order = Order.objects.create(user=self.request.user)
                return order
            case 'list':
                orders = Order.objects.filter(user=self.request.user)
                return orders
            case 'cart':
                user_cart = Cart.objects.filter(user=self.request.user).first()
                return user_cart
            case _:
                order = Order.objects.filter(user=self.request.user, id=kwargs.get('id'))
                return order

    def list(self, request, *args, **kwargs):
        orders = self.get_queryset(action='list')
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["GET", "PATCH"])
    def order(self, request):
        cart = self.get_queryset(action='cart')
        cart_items = CartItems.objects.filter(cart=cart)
        match request.method:

            case "GET":
                order = self.get_queryset(action='create')
                for item in cart_items:
                    OrderItems.objects.create(order=order, price=item.price, product_id=item.product_id)
                cart.delete()
                cart_items.delete()
                return Response(OrderSerializer(order).data)

            case "PATCH":
                order = self.get_queryset(id=request.data['id'])
                order.update(active_flag=request.data['active_flag'])
                return Response(OrderSerializer(order, many=True).data)

    @action(detail=False, methods=["DELETE"])
    def delete(self, request):
        print(request.data)
        order = self.get_queryset(id=request.data['id'])
        order.delete()
        return Response({"Status": "deleted"}, status=204)