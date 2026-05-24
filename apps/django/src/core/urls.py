from django.contrib import admin
from django.http import JsonResponse
from django.urls import path

from core import sso

# Admin is only served under /django; default "View site" would link to http://apps.home/.
admin.site.site_url = "/django/admin/"


def healthz(_request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    # Match ingress pathPrefix /django (no stripPrefix): same path inside the cluster.
    path("django/admin/login/", sso.admin_login, name="admin_login"),
    path("django/sso/login/", sso.sso_login, name="django_sso_login"),
    path("django/sso/callback/", sso.sso_callback, name="django_sso_callback"),
    path("django/admin/", admin.site.urls),
    path("django/healthz", healthz),
]
