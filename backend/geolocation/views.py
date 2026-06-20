import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import DetectWardSerializer
from .service import detect_ward

logger = logging.getLogger(__name__)


class DetectWardView(APIView):
    """
    POST /api/geolocation/detect-ward/

    Pre-validation endpoint. Call this before submitting a grievance to
    confirm GPS coordinates resolve to a known ward and display the ward
    name to the citizen for confirmation.

    No GeolocationLog is written here — logs are written only during
    actual grievance creation (no grievance FK exists at this stage).

    Permission: any authenticated user (citizens and officers).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = DetectWardSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        lat = serializer.validated_data["latitude"]
        lng = serializer.validated_data["longitude"]

        ward = detect_ward(lat, lng)

        if ward is None:
            logger.info(
                "DetectWard: (%.6f, %.6f) — OUTSIDE_BOUNDARY (user=%s)",
                lat, lng, request.user.id,
            )
            return Response(
                {
                    "error": "OUTSIDE_BOUNDARY",
                    "message": (
                        "Coordinates are outside all known ward boundaries. "
                        "Please select your ward manually."
                    ),
                },
                status=status.HTTP_200_OK,
            )

        logger.info(
            "DetectWard: (%.6f, %.6f) -> %s (user=%s)",
            lat, lng, ward.code, request.user.id,
        )
        return Response(
            {
                "ward_id":   ward.id,
                "ward_name": ward.name,
                "ward_code": ward.code,
            },
            status=status.HTTP_200_OK,
        )
