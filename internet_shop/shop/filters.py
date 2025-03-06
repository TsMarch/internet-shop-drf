import json

import django_filters
from django.db.models import Q
from django_filters.rest_framework import FilterSet

from .models import Product


class ProductFilter(FilterSet):
    min_comments = django_filters.NumberFilter(
        field_name="_comment_count", lookup_expr="gte", label="Минимум комментариев"
    )
    min_rating = django_filters.NumberFilter(
        field_name="average_rating", lookup_expr="gte", label="Минимальный рейтинг"
    )
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
        fields = ["min_comments", "min_rating", "filters"]

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
