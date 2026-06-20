from rest_framework.routers import DefaultRouter

from .views import JurisdictionViewSet, RoutingRuleViewSet, WardViewSet

router = DefaultRouter()
router.register("wards", WardViewSet, basename="ward")
router.register("jurisdictions", JurisdictionViewSet, basename="jurisdiction")
router.register("rules", RoutingRuleViewSet, basename="routingrule")

urlpatterns = router.urls
