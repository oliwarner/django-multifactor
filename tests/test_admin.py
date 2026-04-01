from django.contrib import admin
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from multifactor.admin import HasMultifactorFilter, MultiFactorInline, MultifactorUserAdmin
from multifactor.models import KeyTypes, UserKey


class MultifactorAdminTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.site = AdminSite()
        self.user = get_user_model().objects.create_user(
            username="alice",
            email="alice@example.com",
            password="password123",
        )

    def test_has_multifactor_filter_lookups(self):
        f = HasMultifactorFilter(
            request=self.factory.get("/"),
            params={"multifactor": "1"},
            model=UserKey,
            model_admin=admin.ModelAdmin(UserKey, self.site),
        )
        self.assertEqual(f.lookups(None, None), [(True, "Yes"), (False, "No")])

    def test_inline_configuration(self):
        self.assertEqual(MultiFactorInline.model, UserKey)
        self.assertEqual(MultiFactorInline.readonly_fields, ("key_type",))
        self.assertEqual(MultiFactorInline.fields, ("key_type", "enabled"))
        self.assertEqual(MultiFactorInline.max_num, 0)

    def test_user_admin_multifactor_method(self):
        class DummyAdmin(MultifactorUserAdmin, admin.ModelAdmin):
            pass

        ma = DummyAdmin(get_user_model(), self.site)
        obj = type("Obj", (), {"has_multifactors": True})()
        self.assertTrue(ma.multifactor(obj))