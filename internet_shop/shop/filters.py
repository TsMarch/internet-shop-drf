import json

import django_filters
from django.contrib.postgres.search import TrigramSimilarity
from django.db.models import Avg, Count, F, OuterRef, Q, Subquery, Sum, Window
from django_filters.rest_framework import FilterSet

from .models import OrderItems, Product, ReviewComment


class SalesStatisticsFilter(FilterSet):
    product_id = django_filters.NumberFilter(field_name="product_id", lookup_expr="exact")
    date_range = django_filters.DateFromToRangeFilter(field_name="order__created_at")
    category = django_filters.NumberFilter(field_name="product__category", lookup_expr="exact")
    manufacturer = django_filters.CharFilter(field_name="product_manufacturer", lookup_expr="exact")
    price_range = django_filters.RangeFilter(field_name="price")
    rating_min = django_filters.NumberFilter(field_name="rating", lookup_expr="gte", required=False)
    total_orders_min = django_filters.NumberFilter(field_name="total_orders", lookup_expr="gte")
    user = django_filters.NumberFilter(field_name="user_id", lookup_expr="exact")

    class Meta:
        model = OrderItems
        fields = ["date_range", "category", "manufacturer", "price_range", "user", "rating_min"]


class SalesStatisticsQueryBuilder:
    def __init__(self, params):
        self.params = params
        self.group_by_fields = []
        self.queryset = OrderItems.objects.annotate()

    def _add_group_by_fields(self):
        if "category" in self.params:
            self.group_by_fields.append("product__category")
        if "manufacturer" in self.params:
            self.group_by_fields.append("product__manufacturer")
        if "date_range_after" in self.params or "date_range_before" in self.params:
            self.group_by_fields.append("order__created_at")
        if "product_id" in self.params:
            self.group_by_fields.append("product_id")
        if "discount" in self.params:
            self.group_by_fields.append("product__discount")
        if "rating" in self.params:
            self.group_by_fields.append("rating")

        self.group_by_fields.append("order__created_at")

    def _add_rating_subquery(self):
        rating_subquery = (
            ReviewComment.objects.filter(product_id=OuterRef("product_id"), rating__isnull=False)
            .annotate(avg_rating=Window(expression=Avg("rating"), partition_by=[F("product_id")]))
            .values("avg_rating")[:1]
        )
        self.queryset = self.queryset.annotate(rating=Subquery(rating_subquery))

    def _apply_filters(self):
        rating_min = self.params.get("rating_min")
        total_sales_min = self.params.get("total_sales_min")

        if rating_min:
            self.queryset = self.queryset.filter(rating__gte=rating_min)

        if total_sales_min:
            self.queryset = self.queryset.filter(total_orders__gte=total_sales_min)

        if "discount" in self.params:
            self.queryset = self.queryset.annotate(discount=F("product__discount"))

    def _apply_discount(self):
        if "discount" in self.params:
            self.queryset = self.queryset.annotate(discount=F("product__discount"))

    def _add_aggregations(self):
        self.queryset = self.queryset.values(*self.group_by_fields).annotate(
            total_sales=Sum(F("price") * F("quantity")),
            total_orders=Count("order", distinct=True),
            avg_check=Avg(F("price") * F("quantity")),
            date=F("order__created_at"),
        )

    def get_queryset(self):
        self._add_group_by_fields()
        self._add_rating_subquery()
        self._add_aggregations()
        self._apply_filters()

        return self.queryset.order_by("date")


class ProductFilter(FilterSet):
    min_comments = django_filters.NumberFilter(
        field_name="_comment_count", lookup_expr="gte", label="Минимум комментариев"
    )
    min_rating = django_filters.NumberFilter(
        field_name="average_rating", lookup_expr="gte", label="Минимальный рейтинг"
    )
    name = django_filters.CharFilter(method="filter_by_trigram")
    filters = django_filters.CharFilter(method="apply_eav_filters", label="Дополнительные фильтры")
    ordering = django_filters.OrderingFilter(
        fields=(
            ("popularity", "popularity"),
            ("rating", "rating"),
        ),
        field_labels={
            "popularity": "Популярность",
            "rating": "Рейтинг",
        },
    )

    class Meta:
        model = Product
        fields = ["min_comments", "min_rating", "filters", "name"]

    def filter_by_trigram(self, queryset, name, value):
        if not value:
            return queryset
        queryset = (
            queryset.annotate(similarity=TrigramSimilarity("name", value))
            .filter(similarity__gt=0.1)
            .order_by("-similarity")
        )
        return queryset

    def apply_eav_filters(self, queryset, name, value):
        try:
            filters = json.loads(value)
        except ValueError:
            return queryset

        query = Q()
        fields = {field.name for field in Product._meta.get_fields()}

        for attr_name, filter_data in filters.items():
            data_type = filter_data.get("type")
            value = filter_data.get("value")

            match data_type:
                case "text" | "enum":
                    key = attr_name if attr_name in fields else f"eav__{attr_name}"
                    query &= Q(**{f"{key}__in": value})
                case "number":
                    gte = value.get("gte")
                    lte = value.get("lte")
                    key = attr_name if attr_name in fields else f"eav__{attr_name}"
                    self.validate_gte_and_lte(gte, lte)
                    range_filters = {}
                    if gte is not None:
                        range_filters[f"{key}__gte"] = float(gte)
                    if lte is not None:
                        range_filters[f"{key}__lte"] = float(lte)
                    if range_filters:
                        query &= Q(**range_filters)

        return queryset.filter(query)

    def validate_gte_and_lte(self, gte, lte):
        if gte is not None and not isinstance(gte, (int, float)):
            raise ValueError("'gte' must be a number or None")
        if lte is not None and not isinstance(lte, (int, float)):
            raise ValueError("'lte' must be a number or None")
        if gte is not None and lte is not None and gte > lte:
            raise ValueError("Invalid range: 'gte' cannot be greater than 'lte'")
