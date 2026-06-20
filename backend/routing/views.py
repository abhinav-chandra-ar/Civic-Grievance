from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from users.permissions import IsAdmin
from .models import Jurisdiction, RoutingRule, Ward
from .serializers import JurisdictionSerializer, RoutingRuleSerializer, WardSerializer


class WardViewSet(ModelViewSet):
    """
    Wards are listed for authenticated citizens (ward selection on grievance
    submission) but only admins can create, update, or delete them.
    """
    queryset = Ward.objects.order_by("code")
    serializer_class = WardSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated()]
        return [IsAdmin()]


class JurisdictionViewSet(ModelViewSet):
    """Admin-managed; citizens never interact with jurisdictions directly."""
    queryset = Jurisdiction.objects.order_by("name")
    serializer_class = JurisdictionSerializer
    permission_classes = [IsAdmin]


class RoutingRuleViewSet(ModelViewSet):
    """
    Admin-managed mapping of (ward, ML category) → (department, jurisdiction).
    category values must match ml_department_suggestion outputs:
    KSEB | KWA | PWD | PUBLIC_HEALTH | LSG
    """
    queryset = RoutingRule.objects.select_related(
        "ward", "department", "jurisdiction"
    ).order_by("ward__code", "category")
    serializer_class = RoutingRuleSerializer
    permission_classes = [IsAdmin]
