from decimal import Decimal

from django.contrib.auth import get_user_model

# Create your tests here.
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from .models import UserBalance, UserBalanceHistory

User = get_user_model()


class UserBalanceViewSetFixtureTest(TestCase):
    fixtures = ["test_data.json"]

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.get(username="testuser")
        self.client.force_authenticate(user=self.user)

    def test_get_user_balance(self):
        balance = UserBalance.objects.get(user=self.user)
        url = reverse("balance-me")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Decimal(response.data["balance"]), balance.balance)

    def test_check_balance_history(self):
        url = reverse("balance-check-balance-history")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["operation_type"], "deposit")
        self.assertEqual(Decimal(response.data[0]["amount"]), Decimal("30.000000"))

    def test_add_funds(self):
        url = reverse("balance-add-funds")
        response = self.client.patch(url, {"amount": "50.000000"}, format="json")
        self.assertEqual(response.status_code, 200)

        updated_balance = UserBalance.objects.get(user=self.user)
        self.assertEqual(updated_balance.balance, Decimal("150.000000"))

        history = UserBalanceHistory.objects.filter(user=self.user).order_by("-created_at")
        self.assertEqual(history.count(), 2)
        self.assertEqual(history.first().operation_type, "deposit")
        self.assertEqual(history.first().amount, Decimal("50.000000"))
