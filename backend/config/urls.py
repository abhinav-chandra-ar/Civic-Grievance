from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from grievances.views import DepartmentQueueView, NotificationListView, NotificationReadView

urlpatterns = [
    path('admin/', admin.site.urls),
    path("api/", include("users.urls")),
    path('api/departments/', include("departments.urls")),
    path("api/departments/<int:dept_pk>/queue/", DepartmentQueueView.as_view(), name="department-queue"),
    path("api/grievances/", include("grievances.urls")),
    path("api/routing/", include("routing.urls")),
    path("api/geolocation/", include("geolocation.urls")),
    # Module 8 — Notifications (top-level, not nested under grievances)
    path("api/notifications/", NotificationListView.as_view(), name="notification-list"),
    path("api/notifications/<int:pk>/read/", NotificationReadView.as_view(), name="notification-read"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
