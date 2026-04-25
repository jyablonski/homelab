from django.contrib import admin
from django.http import JsonResponse
from django.urls import path


def healthz(_request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    # Match ingress pathPrefix /django (no stripPrefix): same path inside the cluster.
    path("django/admin/", admin.site.urls),
    path("django/healthz", healthz),
]
