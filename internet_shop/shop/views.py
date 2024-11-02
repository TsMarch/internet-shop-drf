from decimal import Decimal

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from .mixins import ModelViewMixin
from .models import Cart, CartItems, Order, OrderItems, Product, User, UserBalance
from .serializers import (
    CartSerializer,
    OrderSerializer,
    ProductListSerializer,
    ProductSerializer,
    UserRegistrationSerializer,
    UserBalanceSerializer
)


class UserBalanceViewSet(ModelViewSet):
    serializer_class = UserBalanceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user_balance, _ = UserBalance.objects.get_or_create(user=self.request.user)
        return user_balance

    def list(self, request, *args, **kwargs):
        user_balance = self.get_queryset()
        serializer = UserBalanceSerializer(user_balance)
        return Response(serializer.data)

    @staticmethod
    def check_balance(cur_balance, amount):
        if cur_balance - amount * -1 < 0:
            raise ValueError

    @action(detail=False, methods=['PATCH'])
    def change_balance(self, request, *args, **kwargs):
        user_balance = self.get_queryset()
        amount = Decimal(request.data.get('amount'))
        if str(amount)[0] == '-':
            try:
                self.check_balance(user_balance.balance, amount)
            except ValueError:
                return Response({"error": "not enough money for transaction"}, status=status.HTTP_400_BAD_REQUEST)
        user_balance.balance += amount
        user_balance.save()
        serializer = self.get_serializer(user_balance)
        return Response(serializer.data, status=status.HTTP_200_OK)


class UserRegistrationViewSet(ModelViewSet):
    serializer_class = UserRegistrationSerializer
    queryset = User.objects.all()
    serializer_action_classes = {
        "list": UserRegistrationSerializer,
        "create": UserRegistrationSerializer,
    }


class ProductViewSet(ModelViewMixin, ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    serializer_action_classes = {
        "list": ProductListSerializer,
        "create": ProductSerializer,
        "retrieve": ProductSerializer,
    }

    @action(methods=["PATCH"], detail=False)
    def update_quantity(self, request, *args, **kwargs):
        products = self.queryset
        new_quantity = request.data.get('available_quantity')
        product_id = request.data.get('id')
        if product_id:
            product = products.filter(id=product_id)
            product.available_quantity = new_quantity
            product.save()
            serializer = self.get_serializer(products.filter(id=product_id), many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response({"error": "no product id in request body"}, status=status.HTTP_404_NOT_FOUND)

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
        user_cart, _ = Cart.objects.get_or_create(user=1)
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
        requested_quantity = int(request.data.get("quantity"))
        match request.method:
            case "POST":
                try:
                    return self.validate_quantity(
                        requested_quantity=requested_quantity,
                        cart=cart,
                        product=product,
                    )
                except CartItems.DoesNotExist:
                    CartItems.objects.create(cart=cart, product=product, quantity=1)
                    return self.validate_quantity(
                        requested_quantity=requested_quantity,
                        cart=cart,
                        product=product,
                    )

            case "PATCH":
                return self.validate_quantity(
                    requested_quantity=request.data.get("quantity"),
                    cart=cart,
                    product=product,
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

    def get_queryset(self, **kwargs):
        return Order.objects.filter(user=self.request.user)

    @action(detail=False, methods=["POST", "PATCH", "DELETE"])
    def order(self, request):
        cart_items = CartItems.objects.filter(cart__user=self.request.user)
        match request.method:
            case "POST":
                order = Order.objects.create(user=self.request.user)
                order_items = []
                for item in cart_items:
                    order_items.append(OrderItems(order=order, price=item.price, product_id=item.product_id))
                OrderItems.objects.bulk_create(order_items)
                cart_items.delete()
                return Response(OrderSerializer(order).data)

            case "PATCH":
                order = Order.objects.filter(user=self.request.user, id=request.data["id"])
                order.update(active_flag=request.data["active_flag"])
                return Response(OrderSerializer(order, many=True).data)

            case "DELETE":
                orders = Order.objects.filter(user=self.request.user)
                for i in orders:
                    i.delete()
                return Response({"status": "deleted orders successfully"}, status=status.HTTP_200_OK)
