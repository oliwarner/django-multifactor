from django.contrib import admin
from django.contrib.auth import get_user_model
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

    def test_filter_queryset_filters_when_value_present(self):
        flt = HasMultifactorFilter(
            request=self.factory.get("/"),
            params={},
            model=UserKey,
            model_admin=admin.ModelAdmin(UserKey, admin.site),
        )
        flt.value = lambda: True

        ma = MultifactorUserAdmin(get_user_model(), admin.site)
        qs = ma.get_queryset(self.factory.get("/"))

        result = flt.queryset(None, qs)

        self.assertIsNotNone(result)

    def test_inline_definition(self):
        self.assertEqual(MultiFactorInline.model, UserKey)
        self.assertEqual(MultiFactorInline.max_num, 0)

    def test_multifactor_user_admin_queryset_annotation(self):
        request = self.factory.get("/")
        request.user = self.superuser

        ma = MultifactorUserAdmin(get_user_model(), admin.site)
        qs = ma.get_queryset(request)

        self.assertTrue(hasattr(qs.query, "annotations"))

    def test_multifactor_user_admin_list_display_includes_flag(self):
        request = self.factory.get("/")
        ma = MultifactorUserAdmin(get_user_model(), admin.site)

        self.assertIn("multifactor", ma.get_list_display(request))

    def test_multifactor_user_admin_list_display_falls_back_when_disabled(self):
        request = self.factory.get("/")
        ma = MultifactorUserAdmin(get_user_model(), admin.site)
        ma.multifactor_list_display = False

        result = ma.get_list_display(request)

        self.assertNotIn("multifactor", result)

    def test_multifactor_user_admin_list_filter_includes_filter(self):
        request = self.factory.get("/")
        ma = MultifactorUserAdmin(get_user_model(), admin.site)

        self.assertIn(HasMultifactorFilter, ma.get_list_filter(request))

    def test_multifactor_user_admin_list_filter_falls_back_when_disabled(self):
        request = self.factory.get("/")
        ma = MultifactorUserAdmin(get_user_model(), admin.site)
        ma.multifactor_filter = False

        result = ma.get_list_filter(request)

        self.assertNotIn(HasMultifactorFilter, result)

    def test_multifactor_returns_boolean_from_annotation(self):
        ma = MultifactorUserAdmin(get_user_model(), admin.site)
        obj = type("Obj", (), {"has_multifactors": True})()

        self.assertTrue(ma.multifactor(obj))

    def test_get_inline_instances_adds_inline_once(self):
        request = self.factory.get("/")
        request.user = self.superuser

        ma = MultifactorUserAdmin(get_user_model(), admin.site)
        ma.inlines = ()
        instances = ma.get_inline_instances(request)

        self.assertTrue(instances)
        self.assertIn(MultiFactorInline, ma.inlines)

    def test_get_inline_instances_does_not_duplicate_inline(self):
        request = self.factory.get("/")
        request.user = self.superuser

        ma = MultifactorUserAdmin(get_user_model(), admin.site)
        ma.inlines = (MultiFactorInline,)

        instances = ma.get_inline_instances(request)

        self.assertTrue(instances)
        self.assertEqual(ma.inlines.count(MultiFactorInline), 1)

    def test_get_inline_instances_respects_disabled_inline_flag(self):
        request = self.factory.get("/")
        request.user = self.superuser

        ma = MultifactorUserAdmin(get_user_model(), admin.site)
        ma.multifactor_inline = False
        ma.inlines = ()

        instances = ma.get_inline_instances(request)

        self.assertEqual(instances, [])
        self.assertNotIn(MultiFactorInline, ma.inlines)

    def test_get_inline_instances_adds_inline_when_enabled(self):
        request = self.factory.get("/")
        request.user = self.superuser

        ma = MultifactorUserAdmin(get_user_model(), admin.site)
        ma.multifactor_inline = True
        ma.inlines = ()

        instances = ma.get_inline_instances(request)

        self.assertTrue(instances)
        self.assertIn(MultiFactorInline, ma.inlines)
        self.assertEqual(ma.inlines.count(MultiFactorInline), 1)