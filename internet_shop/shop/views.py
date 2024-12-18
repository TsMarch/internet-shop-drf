import json
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.decorators import action, api_view
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from .filters import ProductFilter
from .mixins import ModelViewMixin
from .models import (
    Cart,
    CartItems,
    Order,
    Product,
    ProductCategory,
    User,
    UserBalance,
    UserBalanceHistory,
)
from .serializers import (
    CartSerializer,
    CategorySerializer,
    OrderDetailSerializer,
    OrderSerializer,
    ProductListSerializer,
    ProductSerializer,
    UserBalanceHistorySerializer,
    UserBalanceSerializer,
    UserRegistrationSerializer,
)
from .services import (
    AttributeService,
    CartItemsService,
    DepositProcessor,
    ExternalOrderItemsService,
    OrderService,
    PaymentProcessor,
    ProductAttributeService,
    ProductService,
)


@api_view(["POST"])
def delete_attribute(request):
    AttributeService.delete_attribute(
        product_id=request.data.get("product_id"), attribute_name=request.data.get("attribute_name")
    )
    return Response({"status": "successfully deleted"}, status=status.HTTP_200_OK)


class ExternalOrderViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderSerializer

    @action(detail=False, methods=["GET"])
    def order(self, request):
        match request.method:
            case "GET":
                try:
                    order_service = ExternalOrderItemsService(request.data.get("order_data"))
                    order_service.validate_quantity()
                    return Response({"status: successfully reduced product stock"}, status=status.HTTP_200_OK)
                except ValidationError as e:
                    return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


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
        deposit_processor = DepositProcessor()
        deposit_processor.create_balance_history(self.request.user, amount)
        serializer = self.get_serializer(user_balance)
        return Response(serializer.data, status=status.HTTP_200_OK)


class UserRegistrationViewSet(ModelViewSet):
    serializer_class = UserRegistrationSerializer
    queryset = User.objects.all()
    serializer_action_classes = {
        "list": UserRegistrationSerializer,
        "create": UserRegistrationSerializer,
    }


class ProductCategoryViewSet(ModelViewSet):
    queryset = ProductCategory.objects.all()
    serializer_class = CategorySerializer


class ProductViewSet(ModelViewMixin, ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [ProductFilter, DjangoFilterBackend]
    serializer_action_classes = {
        "list": ProductListSerializer,
        "create": ProductSerializer,
        "retrieve": ProductSerializer,
    }

    @staticmethod
    def attrs_handler(attrs, product_id):
        attrs = AttributeService(attributes=attrs).resolve_attributes()
        product = ProductAttributeService(product_id=product_id, attributes=attrs)
        product = product.attach_attribute()
        return product

    @action(methods=["POST"], detail=False)
    def attach_attribute(self, request):
        attrs = json.loads(request.data.get("attributes", []))
        product = ProductViewSet.attrs_handler(attrs, request.data.get("product_id"))
        return Response(ProductSerializer(product).data, status=status.HTTP_200_OK)

    @action(methods=["POST"], detail=False)
    def create_with_attributes(self, request):
        create_product = self.serializer_action_classes["create"](data=request.data)
        create_product.is_valid(raise_exception=True)
        product = create_product.save()
        attrs = json.loads(request.data.get("attributes", []))
        product = ProductViewSet.attrs_handler(attrs, product.id)
        return Response(self.serializer_class(product).data, status=status.HTTP_200_OK)

    @action(methods=["PATCH"], detail=False)
    def update_field(self, request, *args, **kwargs):
        """
        На вход принимается структура данных вида: {product_id: id, name: название поля product, value: value}
        """
        product_service = ProductService(
            product_id=request.data.get("product_id"), field=request.data.get("field_name")
        )
        updated_product = product_service.update_field(request.data.get("field_value"))
        return Response(ProductSerializer(updated_product).data, status=status.HTTP_200_OK)

    @action(methods=["GET"], detail=False)
    def update_price(self, request):
        for product in self.queryset:
            product.price = Decimal(product.old_price - (product.discount * product.old_price) / 100)
        return Response(self.get_serializer(self.queryset, many=True).data, status=status.HTTP_200_OK)

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

    @action(detail=False, methods=["POST", "PATCH", "DELETE"])
    def item(self, request):
        cart = self.get_queryset()
        product = get_object_or_404(Product, pk=request.data.get("product_id"))
        requested_quantity = int(request.data.get("quantity"))
        match request.method:
            case "POST":
                try:
                    validated_cart = CartItemsService.validate_quantity(
                        requested_quantity=requested_quantity,
                        cart=cart,
                        product_id=product.id,
                    )
                    return Response(CartSerializer(validated_cart).data, status=status.HTTP_200_OK)
                except ValueError:
                    return Response({"error": "not enough product"}, status=status.HTTP_400_BAD_REQUEST)
                except CartItems.DoesNotExist:
                    CartItems.objects.create(cart=cart, product=product, quantity=1)
                    validated_cart = CartItemsService.validate_quantity(
                        requested_quantity=requested_quantity,
                        cart=cart,
                        product_id=product.id,
                    )
                    return Response(CartSerializer(validated_cart).data, status=status.HTTP_200_OK)

            case "PATCH":
                try:
                    validated_cart = CartItemsService.validate_quantity(
                        requested_quantity=requested_quantity,
                        cart=cart,
                        product_id=product.id,
                    )
                    return Response(CartSerializer(validated_cart).data, status=status.HTTP_200_OK)
                except ValueError:
                    return Response({"error": "not enough product"}, status=status.HTTP_400_BAD_REQUEST)

            case "DELETE":
                try:
                    CartItems.objects.filter(cart=cart, product=product).delete()
                    return Response(CartSerializer(cart).data, status=status.HTTP_200_OK)
                except CartItems.DoesNotExist:
                    return Response(CartSerializer(cart).data, status=status.HTTP_204_NO_CONTENT)


class OrderViewSet(ModelViewSet, ModelViewMixin):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderSerializer
    serializer_action_classes = {
        "list": OrderSerializer,
        "retrieve": OrderDetailSerializer,
    }

    def get_queryset(self, **kwargs):
        return Order.objects.filter(user=self.request.user)

    @action(detail=False, methods=["GET", "PATCH", "DELETE"])
    def order(self, request):
        match request.method:
            case "GET":
                try:
                    payment_processor = PaymentProcessor()
                    order_service = OrderService(self.request.user, payment_processor)
                    order = order_service.create_order()
                    return Response(self.serializer_class(order).data)
                except ValidationError as e:
                    return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

            case "PATCH":
                order = Order.objects.filter(user=self.request.user, id=request.data["id"])
                order.update(active_flag=request.data["active_flag"])
                return Response(OrderSerializer(order, many=True).data)

            case "DELETE":
                orders = self.get_queryset()
                for order in orders:
                    order.delete()
                return Response({"status": "deleted orders successfully"}, status=status.HTTP_200_OK)
