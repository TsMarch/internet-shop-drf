from django.shortcuts import render, get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, generics
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ViewSet
from .serializers import (
    ProductListSerializer,
    ProductSerializer,
    CartSerializer,
    CartSerializerMixin,
)
from .models import Product, Cart, CartItems
from .mixins import ModelViewMixin


class ProductViewSet(ModelViewMixin, ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    serializer_action_classes = {"list": ProductListSerializer, "create": ProductSerializer, "retrieve": ProductSerializer}


class CartViewSet(CartSerializerMixin, ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Cart.objects.all()
    serializer_class = CartSerializer

    @action(methods=['post'], detail=False)
    def add_product(self, request, validated_data):
        print(validated_data)
        cart, _ = Cart.objects.get_or_create(user=request.user)
        product = Product.objects.get()
        CartItems.objects.get_or_create(cart=cart, product=product.get('product_id'))