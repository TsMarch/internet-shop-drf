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
    CartSerializerMixin, CartItemSerializer,
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

    def destroy(self, request, cart_id, item_id):
        try:
            cart_item = CartItems.objects.get(cart_id=cart_id, product_id=item_id)
            print(cart_item)
            cart_item.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except CartItems.DoesNotExist:
            return Response({"error": "Cart item not found"}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['POST', 'DELETE'])
    def item(self, request):
        match request.method:
            case "POST":
                print("*" * 100, request.data)
                cart = Cart.objects.get(pk=request.data.get("cart_id"))
                product = Product.objects.get(pk=request.data.get("product_id"))
                try:
                    cart_item = CartItems.objects.get(cart=cart, product=product)
                    cart_item.quantity += request.data.get("quantity")
                    cart_item.save()
                except CartItems.DoesNotExist:
                    CartItems.objects.create(cart=cart, product=product, quantity=request.data.get("quantity"))

                return Response(CartSerializer(cart).data, status=status.HTTP_200_OK)

            case "DELETE":
                cart = Cart.objects.get(pk=request.data.get("cart_id"))
                product = Product.objects.get(pk=request.data.get("product_id"))
                try:
                    cart_item = CartItems.objects.get(cart=cart, product=product)
                    cart_item.delete()
                    return Response(CartSerializer(cart).data, status=status.HTTP_200_OK)
                except CartItems.DoesNotExist:
                    return Response(CartSerializer(cart).data, status=status.HTTP_204_NO_CONTENT)



    #    for product_data in cart_items:
     #       if product_id == product_data['product_id']:
      #          obj = CartItems.objects.get(pk=product_data['product_id'])
       #         setattr(obj, 'quantity', quantity)
        #        obj.save()
         #       return Response(ProductSerializer(product).data, status=status.HTTP_201_CREATED)
      #  if product_id in cart:
       #     print("yes")

        #match quantity > product.available_quantity:
         #   case True:
          #      quantity = product.available_quantity

