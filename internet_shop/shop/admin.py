from django.contrib import admin
from .models import ProductCategory, Product, Cart

admin.site.register([Product, ProductCategory, Cart])
