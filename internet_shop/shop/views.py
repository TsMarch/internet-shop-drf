from decimal import Decimal

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from .mixins import ModelViewMixin
from .models import (
    Cart,
    CartItems,
    Order,
    OrderItems,
    Product,
    User,
    UserBalance,
    UserBalanceHistory,
)
from .serializers import (
    CartSerializer,
    OrderSerializer,
    ProductListSerializer,
    ProductSerializer,
    UserBalanceHistorySerializer,
    UserBalanceSerializer,
    UserRegistrationSerializer,
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
    def balance_history(user_id, operation_type, amount):
        match operation_type:
            case "deposit":
                UserBalanceHistory.objects.create(user=user_id, operation_type=operation_type, amount=amount)
            case "payment":
                UserBalanceHistory.objects.create(user=user_id, operation_type=operation_type, amount=amount)

    @action(detail=False, methods=["GET"])
    def check_balance_history(self, request):
        balance_history = UserBalanceHistory.objects.filter(user=self.request.user)
        return Response(UserBalanceHistorySerializer(balance_history, many=True).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["PATCH"])
    def add_funds(self, request, *args, **kwargs):
        user_balance = self.get_queryset()
        amount = Decimal(request.data.get("amount"))
        user_balance.balance += amount
        user_balance.save()
        self.balance_history(self.request.user, "deposit", amount)
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

    @staticmethod
    def product_balance(order, order_data: dict) -> tuple[list[OrderItems], int, list] | Response:
        products = ProductViewSet.queryset.filter(id__in=[i.product_id for i in order_data])
        updated_products = []
        order_sum = 0
        order_items = []
        for product, order_item in zip(products, order_data):
            if product.available_quantity == 0:
                continue
            match product.available_quantity >= order_item.quantity:
                case True:
                    product.available_quantity -= order_item.quantity
                    updated_products.append(product)
                    order_sum += order_item.quantity * product.price
                case False:
                    order_item.quantity = product.available_quantity
                    product.available_quantity = 0
                    updated_products.append(product)
                    order_sum += order_item.quantity * product.price
            order_items.append(
                OrderItems(
                    order=order,
                    price=Decimal(order_item.price),
                    product_id=order_item.product_id,
                    quantity=order_item.quantity,
                )
            )
        if updated_products:
            return order_items, order_sum, updated_products
        else:
            raise ValueError

    @action(methods=["PATCH"], detail=False)
    def update_quantity(self, request, *args, **kwargs):
        """
        На вход принимается структура данных вида: {id_товара: количество товара}
        """
        products = ProductViewSet.queryset.filter(id__in=request.data.keys())
        for product in products:
            product.available_quantity = request.data[str(product.id)]
        try:
            Product.objects.bulk_update(products, ["available_quantity"])
        except ValueError:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        return Response(ProductSerializer(products, many=True).data, status=status.HTTP_200_OK)

    @action(methods=["GET"], detail=False)
    def search(self, request):
        products = self.queryset
        category_id = request.query_params.get("category_id")
        name = request.query_params.get("name")
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
                    cart_item.quantity = requested_quantity
                    cart_item.save()

        return Response(CartSerializer(cart).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["POST", "PATCH", "DELETE"])
    def item(self, request):
        cart = self.get_queryset()
        product = get_object_or_404(Product, pk=request.data.get("product_id"))
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

    @staticmethod
    def validate_order(**kwargs):
        pass

    @action(detail=False, methods=["GET", "PATCH", "DELETE"])
    def order(self, request):
        match request.method:
            case "GET":
                cart_items = CartItems.objects.filter(cart__user=self.request.user)
                user_balance = UserBalance.objects.get(user=self.request.user)
                order = Order.objects.create(user=self.request.user)
                try:
                    order_items, order_sum, updated_products = ProductViewSet.product_balance(order, cart_items)
                except ValueError:
                    return Response(status=status.HTTP_400_BAD_REQUEST)
                match user_balance.balance >= order_sum:
                    case True:
                        user_balance.balance -= order_sum
                        Product.objects.bulk_update(updated_products, ["available_quantity"])
                        user_balance.save()
                    case False:
                        return Response({"error": "not enough money"}, status=status.HTTP_400_BAD_REQUEST)
                UserBalanceViewSet.balance_history(self.request.user, "payment", order_sum)
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
