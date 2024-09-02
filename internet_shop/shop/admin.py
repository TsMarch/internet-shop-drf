from django.contrib import admin

from .models import Cart, CartItems, Product, ProductCategory, Order, OrderItems


class ProductAdmin(admin.ModelAdmin):
    model = Product
    exclude = ["price"]


class CartItemsInlineAdmin(admin.TabularInline):
    model = CartItems
    extra = 1


class CartAdmin(admin.ModelAdmin):
    inlines = [CartItemsInlineAdmin]


class OrderItemsInlineAdmin(admin.TabularInline):
    model = OrderItems
    extra = 1

class OrderAdmin(admin.ModelAdmin):
    inlines = [OrderItemsInlineAdmin]

admin.site.register(Product, ProductAdmin)
admin.site.register(Cart, CartAdmin)
admin.site.register(ProductCategory)
admin.site.register(Order, OrderAdmin)