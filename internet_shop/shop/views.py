from django.shortcuts import render, get_object_or_404
from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ViewSet
from .serializers import (
    ProductSerializer,
    ProductListSerializer,
    ProductSerializerMixin,
    CartSerializer,
    CartItemSerializer,
    CartSerializerMixin,
)
from .models import Product, Cart, CartItems


class ProductViewSet(ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductListSerializer
    serializer_action_classes = {"list": ProductListSerializer, "retrieve": ProductSerializer}


class CartViewSet(CartSerializerMixin, ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Cart.objects.all()
    serializer_class = CartSerializer
    serializer_action_classes = {"list": CartSerializer, "create": CartSerializer}
