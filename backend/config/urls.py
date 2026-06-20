from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from grievances.views import DepartmentQueueView

urlpatterns = [
    path('admin/', admin.site.urls),
    path("api/", include("users.urls")),
    path('api/departments/', include("departments.urls")),
    path("api/departments/<int:dept_pk>/queue/", DepartmentQueueView.as_view(), name="department-queue"),
    path("api/grievances/", include("grievances.urls")),
    path("api/routing/", include("routing.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
