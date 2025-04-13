import json

import django_filters
from django.contrib.postgres.search import (
    SearchQuery,
    SearchRank,
    SearchVector,
    TrigramWordSimilarity,
)
from django.db.models import Avg, Count, F, Q, Sum
from django_filters.rest_framework import FilterSet

from .models import OrderItems, Product


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

    def get_queryset(self):
        self._add_group_by_fields()
        self._add_rating()
        self._add_aggregations()

        return self.queryset.order_by("date")

    def _add_group_by_fields(self):

        group_by_mapping = {
            "category": {"field": "product__category", "annotations": {"category_name": F("product__category__name")}},
            "manufacturer": {"field": "product__manufacturer", "annotations": {}},
            "date": {"field": "order__created_at", "annotations": {}},
            "product": {
                "field": "product_id",
                "annotations": {"product_name": F("product__name"), "product_quantity": F("quantity")},
            },
            "discount": {"field": "product__discount", "annotations": {}},
            "user": {
                "field": "order__user_id",
                "annotations": {"user_email": F("order__user__email"), "user_id": F("order__user_id")},
            },
        }

        group_by_param = self.params.get("group_by", "")
        fields = group_by_param.split(",") if group_by_param else []

        self.group_by_fields = []
        self.additional_annotations = {}

        for field in fields:
            if field in group_by_mapping:
                mapping = group_by_mapping[field]
                self.group_by_fields.append(mapping["field"])
                self.additional_annotations.update(mapping.get("annotations", {}))

        if not self.group_by_fields:
            self.group_by_fields = ["order__created_at"]

    def _add_rating(self):
        self.queryset = self.queryset.annotate(rating=Avg("product__reviews__rating"))

    def _add_aggregations(self):
        self.queryset = self.queryset.annotate(**self.additional_annotations)

        self.queryset = self.queryset.values(
            *self.group_by_fields, *self.additional_annotations.keys(), "rating"
        ).annotate(
            total_sales=Sum(F("price") * F("quantity")),
            total_orders=Count("order", distinct=True),
            total_discount=Sum((F("product__old_price") - F("price")) * F("quantity")),
            avg_check=Avg(F("price") * F("quantity")),
            date=F("order__created_at"),
        )


class ProductFilter(FilterSet):
    min_comments = django_filters.NumberFilter(
        field_name="_comment_count", lookup_expr="gte", label="Минимум комментариев"
    )
    min_rating = django_filters.NumberFilter(
        field_name="average_rating", lookup_expr="gte", label="Минимальный рейтинг"
    )
    search = django_filters.CharFilter(method="search_with_trigram")
    search_vector = django_filters.CharFilter(method="search_with_vector")
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
        fields = ["min_comments", "min_rating", "filters", "search"]

    def search_with_trigram(self, queryset, name, value):
        if not value:
            return queryset

        direct_queryset = queryset.filter(
            Q(name__icontains=value)
            | Q(description__icontains=value)
            | Q(category__name__icontains=value)
            | Q(category__parent__name__icontains=value)
        )
        if direct_queryset.exists():
            return direct_queryset

        similarity_fields = {
            "similarity_name": "name",
            "similarity_description": "description",
            "similarity_category": "category__name",
            "similarity_category_parent": "category__parent__name",
        }

        for alias, field in similarity_fields.items():
            queryset = queryset.annotate(**{alias: TrigramWordSimilarity(value, field)})

        trigram_filters = Q()

        for alias in similarity_fields:
            trigram_filters |= Q(**{f"{alias}__gt": 0.4})

        return queryset.filter(trigram_filters).order_by(
            "-similarity_name",
            "-similarity_description",
            "-similarity_category",
            "-similarity_category_parent",
        )

    def search_with_vector(self, queryset, name, value):
        if not value:
            return queryset

        return (
            queryset.annotate(
                search=SearchVector(
                    "name",
                    "description",
                    "category__name",
                    "category__parent__name",
                ),
                rank=SearchRank(F("search"), SearchQuery(value)),
            )
            .filter(search=SearchQuery(value))
            .order_by("-rank")
        )

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
