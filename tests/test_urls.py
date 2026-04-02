from django.test import SimpleTestCase
from django.urls import reverse, resolve

from multifactor import views


class UrlsTests(SimpleTestCase):
    def test_home_url_resolves(self):
        match = resolve("/admin/multifactor/")
        self.assertEqual(match.func.view_class, views.List)

    def test_help_url_resolves(self):
        match = resolve("/admin/multifactor/help/")
        self.assertEqual(match.func.view_class, views.Help)

    def test_add_url_resolves(self):
        match = resolve("/admin/multifactor/add/")
        self.assertEqual(match.func.view_class, views.Add)

    def test_reverse_home(self):
        self.assertEqual(reverse("multifactor:home"), "/admin/multifactor/")

    def test_reverse_help(self):
        self.assertEqual(reverse("multifactor:help"), "/admin/multifactor/help/")

    def test_reverse_add(self):
        self.assertEqual(reverse("multifactor:add"), "/admin/multifactor/add/")