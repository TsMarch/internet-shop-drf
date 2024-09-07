from django.contrib import admin

from .models import Cart, CartItems, Product, ProductCategory

class ProductAdmin(admin.ModelAdmin):
    model = Product
    exclude = ["price"]


class CartItemsInlineAdmin(admin.TabularInline):
    model = CartItems
    extra = 1


class CartAdmin(admin.ModelAdmin):
    inlines = [CartItemsInlineAdmin]




admin.site.register(Product, ProductAdmin)
admin.site.register(Cart, CartAdmin)
admin.site.register(ProductCategory)
