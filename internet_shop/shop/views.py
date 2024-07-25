from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Product


class ListProducts(APIView):
    def get(self, request):
        products = {
            product.name: [
                {
                    "Цена": product.price,
                    "Доступное количество на складе": product.available_quantity,
                    "Описание": product.description,
                }
            ]
            for product in Product.objects.all()
        }
        return Response(products)
