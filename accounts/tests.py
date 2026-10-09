import re

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse


class AccountSecurityTests(TestCase):
    def test_registration_applies_password_validators_and_never_grants_admin(self):
        client = Client(enforce_csrf_checks=True)
        page = client.get(reverse("register"))
        csrf_token = re.search(
            rb'name="csrfmiddlewaretoken" value="([^"]+)"', page.content
        ).group(1).decode()
        data = {
            "username": "applicant_test_01",
            "email": "applicant_test_01@example.test",
            "password": "weak",
            "confirm_password": "weak",
            "csrfmiddlewaretoken": csrf_token,
        }
        response = client.post(reverse("register"), data)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(User.objects.filter(username=data["username"]).exists())

        data["password"] = data["confirm_password"] = "R4ndom!Passphrase-9831"
        response = client.post(reverse("register"), data)
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username=data["username"])
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_logout_requires_post(self):
        user = User.objects.create_user(username="logout_test", password="test-passphrase")
        client = Client()
        client.force_login(user)
        self.assertEqual(client.get(reverse("logout")).status_code, 405)
        self.assertEqual(client.session.get("_auth_user_id"), str(user.pk))
        self.assertEqual(client.post(reverse("logout")).status_code, 302)
        self.assertNotIn("_auth_user_id", client.session)
