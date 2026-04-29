from django.test import TestCase
from django.urls import reverse


class FrontendRouteTests(TestCase):
    def test_home_page_loads(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "AsseTrack")

    def test_login_page_loads(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Access Role")

    def test_head_office_console_page_loads(self):
        response = self.client.get(reverse("head-office-console"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Head Office Manager")
