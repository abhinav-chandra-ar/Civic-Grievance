from rest_framework import serializers


class DetectWardSerializer(serializers.Serializer):
    """
    Input serializer for POST /api/geolocation/detect-ward/

    Validates that coordinates are valid WGS84 values. The Trivandrum
    bounding box check is intentionally omitted here — the service returns
    OUTSIDE_BOUNDARY for any point not within a ward polygon, which gives
    a clear response for out-of-area coordinates.
    """
    latitude  = serializers.FloatField(min_value=-90.0,  max_value=90.0)
    longitude = serializers.FloatField(min_value=-180.0, max_value=180.0)
