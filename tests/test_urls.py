from django.test import SimpleTestCase
from django.urls import reverse, resolve

from multifactor import views


class UrlsTests(SimpleTestCase):
    def test_home_url_resolves(self):
        match = resolve("/multifactor/")
        self.assertEqual(match.func.view_class, views.List)

    def test_help_url_resolves(self):
        match = resolve("/multifactor/help/")
        self.assertEqual(match.func.view_class, views.Help)

    def test_add_url_resolves(self):
        match = resolve("/multifactor/add/")
        self.assertEqual(match.func.view_class, views.Add)

    def test_reverse_home(self):
        self.assertEqual(reverse("multifactor:home"), "/multifactor/")