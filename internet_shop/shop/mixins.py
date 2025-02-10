from .models import Order


class ModelViewMixin:
    def get_serializer_class(self):
        try:
            return self.serializer_action_classes[self.action]
        except (KeyError, AttributeError):
            return super().get_serializer_class()


class PurchasedProductMixin:
    def has_purchased_product(self, user, product):
        error = False
        if not Order.objects.filter(user=user, products=product).exists():
            error = True
        return error
