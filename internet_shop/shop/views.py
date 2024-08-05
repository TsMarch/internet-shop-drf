from django.shortcuts import render, get_object_or_404
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from .serializers import ProductSerializer, ProductListSerializer
from .models import Product


class ProductViewSet(ViewSet):
    def list(self, request):
        queryset = Product.objects.all()
        serializer = ProductListSerializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, name=None):
        try:
            product = Product.objects.get(name=name)
            serializer = ProductSerializer(product)
            return Response(serializer.data)
        except Product.DoesNotExist:
            return Response(status=404)


