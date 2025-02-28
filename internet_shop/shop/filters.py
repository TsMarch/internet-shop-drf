import json

from django.db.models import Avg, Count, Field, Q
from rest_framework.filters import BaseFilterBackend

from .models import Product


class ProductFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        eav_filters = request.query_params.get("filters")
        min_comments = request.query_params.get("min_comments")
        min_rating = request.query_params.get("min_rating")

        query = Q()

        if eav_filters:
            try:
                filters = json.loads(eav_filters)
            except ValueError:
                return queryset
            fields = [field.name for field in Product._meta.get_fields() if isinstance(field, Field)]

            for attr_name, filter_data in filters.items():
                data_type = filter_data.get("type")
                value = filter_data.get("value")

                match data_type:
                    case "text" | "enum":
                        if attr_name in fields:
                            query &= Q(**{f"{attr_name}__in": value})
                        else:
                            query &= Q(**{f"eav__{attr_name}__in": value})

                    case "number":
                        gte = float(value["gte"]) if value.get("gte") is not None else None
                        lte = float(value["lte"]) if value.get("lte") is not None else None
                        prefix = attr_name if attr_name in fields else f"eav__{attr_name}"
                        self._validate_gte_and_lte(gte=gte, lte=lte)
                        filters = {}
                        if gte is not None:
                            filters[f"{prefix}__gte"] = gte
                        if lte is not None:
                            filters[f"{prefix}__lte"] = lte

                        if filters:
                            query &= Q(**filters)

        if min_comments is not None:
            try:
                min_comments = int(min_comments)
                queryset = queryset.annotate(comment_count=Count("reviews"))
                query &= Q(comment_count__gte=min_comments)
            except ValueError:
                pass

        if min_rating is not None:
            try:
                min_rating = float(min_rating)
                queryset = queryset.annotate(avg_rating=Avg("reviews__rating"))
                query &= Q(avg_rating__gte=min_rating)
            except ValueError:
                pass

        return queryset.filter(query)

    def _validate_gte_and_lte(self, **kwargs):
        if kwargs["gte"] is not None and not isinstance(kwargs["gte"], (float, int)):
            raise ValueError("'gte' must be a number or None")
        if kwargs["lte"] is not None and not isinstance(kwargs["lte"], (float, int)):
            raise ValueError("'lte' must be a number or None")
        if kwargs["gte"] is not None and kwargs["lte"] is not None and kwargs["gte"] > kwargs["lte"]:
            raise ValueError("Invalid range: 'gte' cannot be greater than 'lte'")

        return kwargs
