import logging

from django.contrib.gis.geos import Point

from routing.models import Ward

logger = logging.getLogger(__name__)


def detect_ward(lat: float, lng: float) -> Ward | None:
    """
    Perform a PostGIS point-in-polygon lookup to identify which ward
    contains the given GPS coordinates.

    Arguments:
        lat: WGS84 latitude  (y-axis, device GPS output)
        lng: WGS84 longitude (x-axis, device GPS output)

    Returns:
        Ward instance if exactly one ward boundary contains the point.
        None if the point falls outside all known ward boundaries.

    Notes:
        - Point(lng, lat) — PostGIS/WGS84 uses (x, y) = (longitude, latitude).
        - Wards with boundary=None are automatically excluded by the filter.
        - If multiple wards match (boundary overlap in source data), the first
          is returned and a WARNING is logged. This indicates a data quality
          issue in the imported GeoJSON that should be corrected.
        - No nearest-centroid or fallback guessing is performed.
    """
    point = Point(lng, lat, srid=4326)

    matches = list(
        Ward.objects
        .filter(boundary__contains=point)
        .only("id", "name", "code")
    )

    if not matches:
        logger.debug(
            "GPS point (%.6f, %.6f) is outside all ward boundaries.",
            lat, lng,
        )
        return None

    if len(matches) > 1:
        logger.warning(
            "GPS point (%.6f, %.6f) matched %d wards: %s. "
            "Boundary overlap detected in source data. Returning first match.",
            lat, lng,
            len(matches),
            [w.code for w in matches],
        )

    return matches[0]
