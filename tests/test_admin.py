from django.contrib import admin
from django.contrib.auth import get_user_model
from django.db.models import QuerySet
from django.test import RequestFactory, TestCase

from multifactor.admin import HasMultifactorFilter, MultiFactorInline, MultifactorUserAdmin
from multifactor.models import KeyTypes, UserKey


class AdminTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = get_user_model().objects.create_user(
            username="alice",
            email="alice@example.com",
            password="password123",
        )
        self.superuser = get_user_model().objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="password123",
        )

    def test_filter_lookups(self):
        flt = HasMultifactorFilter(
            request=self.factory.get("/"),
            params={},
            model=UserKey,
            model_admin=admin.ModelAdmin(UserKey, admin.site),
        )

        self.assertEqual(flt.lookups(None, None), [(True, "Yes"), (False, "No")])

    def test_filter_queryset_returns_none_when_empty(self):
        flt = HasMultifactorFilter(
            request=self.factory.get("/"),
            params={},
            model=UserKey,
            model_admin=admin.ModelAdmin(UserKey, admin.site),
        )
        self.assertIsNone(flt.queryset(None, UserKey.objects.all()))

    def test_inline_definition(self):
        self.assertEqual(MultiFactorInline.model, UserKey)
        self.assertEqual(MultiFactorInline.max_num, 0)

    def test_multifactor_user_admin_queryset_annotation(self):
        request = self.factory.get("/")
        request.user = self.superuser

        ma = MultifactorUserAdmin(get_user_model(), admin.site)
        qs = ma.get_queryset(request)

        self.assertIsInstance(qs, QuerySet)

    def test_multifactor_user_admin_list_display_includes_flag(self):
        request = self.factory.get("/")
        ma = MultifactorUserAdmin(get_user_model(), admin.site)

        self.assertIn("multifactor", ma.get_list_display(request))

    def test_multifactor_user_admin_list_filter_includes_filter(self):
        request = self.factory.get("/")
        ma = MultifactorUserAdmin(get_user_model(), admin.site)

        self.assertIn(HasMultifactorFilter, ma.get_list_filter(request))
