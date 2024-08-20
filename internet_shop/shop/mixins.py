class ModelViewMixin:
    def get_serializer_class(self):
        try:
            print(self.serializer_action_classes)
            return self.serializer_action_classes[self.action]
        except (KeyError, AttributeError):
            return super().get_serializer_class()
