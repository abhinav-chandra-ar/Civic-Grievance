from rest_framework.routers import DefaultRouter
from .views import DepartmentViewSet

router = DefaultRouter()
router.register("", DepartmentViewSet)

urlpatterns = router.urls