from django.contrib import admin
from django.urls import path, include

from decorator_include import decorator_include
from multifactor.decorators import multifactor_protected


urlpatterns = [
    path('admin/multifactor/', include('multifactor.urls')),
    path('admin/', decorator_include(multifactor_protected(factors=1), admin.site.urls)),
]
