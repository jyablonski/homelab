from django.contrib import admin
from django.http import JsonResponse
from django.urls import path

from core import sso

# Default "View site" would link to the host root, which has no page.
admin.site.site_url = "/admin/"


def healthz(_request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("admin/login/", sso.admin_login, name="admin_login"),
    path("sso/login/", sso.sso_login, name="django_sso_login"),
    path("sso/callback/", sso.sso_callback, name="django_sso_callback"),
    path("admin/", admin.site.urls),
    path("healthz", healthz),
]
