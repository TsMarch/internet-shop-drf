import json

import django_filters
from django.contrib.postgres.search import TrigramSimilarity
from django.db.models import Q
from django_filters.rest_framework import FilterSet

from .models import OrderItems, Product


class SalesStatisticsFilter(FilterSet):
    start_date = django_filters.DateFilter(field_name="created_at", lookup_expr="gte")
    end_date = django_filters.DateFilter(field_name="created_at", lookup_expr="lte")  # До
    category = django_filters.CharFilter(field_name="products__category", lookup_expr="exact")
    manufacturer = django_filters.CharFilter(field_name="products__manufacturer", lookup_expr="exact")
    min_price = django_filters.NumberFilter(field_name="total_sum", lookup_expr="gte")
    max_price = django_filters.NumberFilter(field_name="total_sum", lookup_expr="lte")
    total_sales = django_filters.NumberFilter(field_name="")
    user = django_filters.NumberFilter(field_name="user_id", lookup_expr="exact")

    class Meta:
        model = OrderItems
        fields = ["start_date", "end_date", "category", "manufacturer", "min_price", "max_price", "user"]


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
