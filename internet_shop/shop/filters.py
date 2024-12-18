import json

from django.db.models import Q
from rest_framework.filters import BaseFilterBackend


class ProductEAVFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        eav_filters = request.query_params.get("filters")
        if not eav_filters:
            return queryset

        try:
            filters = json.loads(eav_filters)
        except ValueError:
            return queryset

        eav_query = Q()
        for attr_name, filter_data in filters.items():
            data_type = filter_data.get("type")
            value = filter_data.get("value")

            if data_type == "text":
                gte = value.get("gte")
                lte = value.get("lte")
                if gte is not None:
                    eav_query &= Q(**{f"{attr_name}__gte": gte})
                if lte is not None:
                    eav_query &= Q(**{f"{attr_name}__lte": lte})

        # elif data_type == "text":
        #    eav_query &= Q(**{f"eav__{attr_name}__in": value})

        # elif data_type == "enum":
        #   eav_query &= Q(**{f"eav__{attr_name}__in": value})

        return queryset.filter(eav_query)
