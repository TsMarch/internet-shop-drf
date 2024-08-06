from django.shortcuts import render, get_object_or_404
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ViewSet
from .serializers import ProductSerializer, ProductListSerializer
from .models import Product


class ProductViewSet(ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductListSerializer
    serializer_action_classes = {"list": ProductListSerializer, "retrieve": ProductSerializer}
