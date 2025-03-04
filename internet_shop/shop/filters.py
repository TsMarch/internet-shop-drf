import json

from django.db.models import Avg, Count, ExpressionWrapper, F, IntegerField, Q, Sum
from django.db.models.functions import Coalesce
from rest_framework.filters import BaseFilterBackend

from .models import Product


class ProductFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        for filter_func in [
            self.apply_eav_filters,
            self.apply_min_comments_filter,
            self.apply_min_rating_filter,
            self.annotate_queryset,
            self.apply_ordering,
        ]:
            queryset = filter_func(request, queryset)
        return queryset

    def apply_eav_filters(self, request, queryset):
        eav_filters = request.query_params.get("filters")
        if not eav_filters:
            return queryset

        try:
            filters = json.loads(eav_filters)
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

    def apply_min_comments_filter(self, request, queryset):
        min_comments = request.query_params.get("min_comments")
        if min_comments is None:
            return queryset

        try:
            min_comments = int(min_comments)
            return queryset.annotate(comment_count=Count("reviews")).filter(comment_count__gte=min_comments)
        except ValueError:
            return queryset

    def apply_min_rating_filter(self, request, queryset):
        min_rating = request.query_params.get("min_rating")
        if min_rating is None:
            return queryset

        try:
            min_rating = float(min_rating)
            return queryset.annotate(avg_rating=Avg("reviews__rating")).filter(avg_rating__gte=min_rating)
        except ValueError:
            return queryset

    def annotate_queryset(self, request, queryset):
        return queryset.annotate(
            review_count=Count("reviews", filter=Q(reviews__parent=None)),
            comment_count=Count("reviews", filter=Q(reviews__parent__isnull=False)),
            sales_count=Coalesce(Sum("orders__items__quantity"), 0),
            popularity=ExpressionWrapper(
                F("sales_count") + F("comment_count") * F("review_count"),
                output_field=IntegerField(),
            ),
        )

    def apply_ordering(self, request, queryset):
        ordering = request.query_params.get("ordering")
        if not ordering:
            return queryset

        ordering_fields = {"popularity": "-popularity", "-popularity": "popularity"}
        return queryset.order_by(ordering_fields.get(ordering, "-popularity"))

    def validate_gte_and_lte(self, gte, lte):
        if gte is not None and not isinstance(gte, (int, float)):
            raise ValueError("'gte' must be a number or None")
        if lte is not None and not isinstance(lte, (int, float)):
            raise ValueError("'lte' must be a number or None")
        if gte is not None and lte is not None and gte > lte:
            raise ValueError("Invalid range: 'gte' cannot be greater than 'lte'")
