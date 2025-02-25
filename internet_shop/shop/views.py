import json
import logging
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import Avg, Count, Prefetch
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.decorators import action, api_view
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from .filters import ProductFilter
from .mixins import ModelViewMixin
from .models import (
    Cart,
    CartItems,
    Order,
    Product,
    ProductCategory,
    ReviewComment,
    User,
    UserBalance,
    UserBalanceHistory,
)
from .pagination import ReviewPagination
from .serializers import (
    CartSerializer,
    CategorySerializer,
    OrderDetailSerializer,
    OrderSerializer,
    ProductListSerializer,
    ProductSerializer,
    RootReviewSerializer,
    UserBalanceHistorySerializer,
    UserBalanceSerializer,
    UserRegistrationSerializer,
)
from .services import (
    AttributeService,
    CartItemsService,
    DepositProcessor,
    ExternalOrderItemsService,
    FileProcessorFactory,
    OrderService,
    PaymentProcessor,
    ProductAttributeService,
    ProductFileProcessor,
    ProductService,
    ReviewCreateService,
)

logger = logging.getLogger(__name__)


@api_view(["POST"])
def delete_attribute(request):
    AttributeService.delete_attribute(
        product_id=request.data.get("product_id"), attribute_name=request.data.get("attribute_name")
    )
    return Response({"status": "successfully deleted"}, status=status.HTTP_200_OK)


class ReviewCommentViewSet(GenericViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["POST"])
    def create_review(self, request):
        user = self.request.user
        product_id = request.data.get("product_id")
        rating_value = request.data.get("rating")
        text = request.data.get("text")

        try:
            service = ReviewCreateService(product_id=product_id, user=user)
            review = service.create_review(text, rating_value)
            serializer = RootReviewSerializer(review)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["POST"])
    def create_comment(self, request):
        user = self.request.user
        product = Product.objects.filter(id=request.data.get("product_id"))
        text = request.data.get("text")
        parent = request.data.get("parent")
        ReviewComment.objects.create(user=user, product=product, text=text, parent=parent)
        return Response("comment successfully create", status=status.HTTP_200_OK)


class ExternalOrderViewSet(GenericViewSet):
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


class UserBalanceViewSet(RetrieveModelMixin, GenericViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user_balance, _ = UserBalance.objects.get_or_create(user=self.request.user)
        return user_balance

    def get_serializer_class(self):
        if self.action == "check_balance_history":
            return UserBalanceHistorySerializer
        return UserBalanceSerializer

    @action(detail=False, methods=["GET"])
    def check_balance_history(self, request):
        balance_history = UserBalanceHistory.objects.filter(user=self.request.user)
        serializer = self.get_serializer(balance_history, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

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


class UserRegistrationViewSet(CreateModelMixin, GenericViewSet):
    serializer_class = UserRegistrationSerializer
    queryset = User.objects.all()
    serializer_action_classes = {
        "list": UserRegistrationSerializer,
        "create": UserRegistrationSerializer,
    }


class ProductCategoryViewSet(CreateModelMixin, GenericViewSet, RetrieveModelMixin):
    queryset = ProductCategory.objects.all()
    serializer_class = CategorySerializer

    def retrieve(self, request, *args, **kwargs):
        pass


class ProductViewSet(ModelViewMixin, RetrieveModelMixin, CreateModelMixin, ListModelMixin, GenericViewSet):
    serializer_class = ProductListSerializer
    filter_backends = [ProductFilter, DjangoFilterBackend]
    serializer_action_classes = {
        "list": ProductListSerializer,
        "create": ProductSerializer,
        "retrieve": ProductSerializer,
        "filter_by_category": ProductListSerializer,
        "get_nested_comments": RootReviewSerializer,
    }
    pagination_class = ReviewPagination

    def get_object(self):
        product = Product.objects.prefetch_related(
            Prefetch(
                "reviews",
                queryset=ReviewComment.objects.filter(parent__isnull=True)
                .order_by("created_at")
                .select_related("user"),
            ),
            Prefetch("reviews__children", queryset=ReviewComment.objects.select_related("user")),
        ).get(id=self.kwargs["pk"])
        return product

    def retrieve(self, request, *args, **kwargs):
        product = self.get_object()
        queryset = (
            product.reviews.filter(parent__isnull=True)
            .select_related("user")
            .prefetch_related(Prefetch("children", queryset=ReviewComment.objects.select_related("user")))
            .order_by("created_at")
        )
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        if page is not None:
            reviews_data = RootReviewSerializer(page, many=True).data
            reviews_paginated = paginator.get_paginated_response(reviews_data).data
        else:
            reviews_paginated = RootReviewSerializer(queryset, many=True).data
        product_data = ProductSerializer(product).data
        product_data["reviews"] = reviews_paginated

        return Response(product_data, status=status.HTTP_200_OK)

    def get_queryset(self):
        if self.action == "list":
            return Product.objects.select_related("category").annotate(
                average_rating=Avg("reviews__rating"), rating_count=Count("reviews__rating")
            )
        return Product.objects.all()

    @staticmethod
    def attrs_handler(attrs, product_id):
        attrs = AttributeService(attributes=attrs).resolve_attributes()
        product = ProductAttributeService(product_id=product_id, attributes=attrs)
        product = product.attach_attribute()
        return product

    @action(methods=["GET"], detail=False, url_path="category/(?P<category_id>\\d+)")
    def filter_by_category(self, request, category_id=None):
        root_category = ProductCategory.objects.get(id=category_id)
        descendants = root_category.get_descendants(include_self=True)
        products = (
            self.get_queryset()
            .filter(category__in=descendants)
            .select_related("category")
            .prefetch_related("eav_values__attribute")
        )
        serialized_products = self.get_serializer(products, many=True).data
        return Response(serialized_products, status=status.HTTP_200_OK)

    @action(methods=["GET"], detail=True, url_path="comments/(?P<comment_id>\\d+)")
    def get_nested_comments(self, request, pk=None, comment_id=None):
        try:
            root_comment = ReviewComment.objects.get(id=comment_id, product_id=pk)
            descendants = root_comment.get_descendants(include_self=True).select_related("user")

            comment_map = {comment.id: comment for comment in descendants}

            for comment in descendants:
                comment.children_list = []

            for comment in descendants:
                if comment.parent_id and comment.parent_id in comment_map:
                    comment_map[comment.parent_id].children_list.append(comment)

            serializer = self.get_serializer(descendants, many=True).data
            return Response(serializer, status=status.HTTP_200_OK)

        except ReviewComment.DoesNotExist:
            return Response({"error": "no such comment"}, status=status.HTTP_404_NOT_FOUND)

    @action(methods=["POST"], detail=False, parser_classes=[MultiPartParser, FormParser])
    def upload_products_file(self, request):
        file = request.FILES.get("file")
        if not file:
            return Response({"error": "Файл не загружен"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            file_processor = FileProcessorFactory.get_processor(file.name)
            product_processor = ProductFileProcessor(file_processor=file_processor, file=file)
            product_processor.create_products()
            return Response("new products created", status=status.HTTP_200_OK)
        except ValueError as e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["POST"], detail=False)
    def attach_attribute(self, request):
        attrs = request.data.get("attributes", [])
        product = self.attrs_handler(attrs, request.data.get("product_id"))
        return Response(self.serializer_class(product).data, status=status.HTTP_200_OK)

    @action(methods=["POST"], detail=False)
    def create_with_attributes(self, request):
        create_product = self.serializer_action_classes["create"](data=request.data)
        create_product.is_valid(raise_exception=True)
        product = create_product.save()
        attrs = json.loads(request.data.get("attributes", []))
        product = self.attrs_handler(attrs, product.id)
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
        return Response(self.serializer_class(updated_product).data, status=status.HTTP_200_OK)

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


class CartViewSet(GenericViewSet, RetrieveModelMixin, CreateModelMixin, ListModelMixin):
    permission_classes = [IsAuthenticated]
    serializer_class = CartSerializer

    def get_queryset(self):
        user_cart, created = Cart.objects.get_or_create(user=self.request.user)
        if created:
            return user_cart
        return Cart.objects.prefetch_related("items__product").get(id=user_cart.id)

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


class OrderViewSet(GenericViewSet, ModelViewMixin):
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
