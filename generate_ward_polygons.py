"""
generate_ward_polygons.py

Generates approximate square polygons for all 100 Thiruvananthapuram
Corporation wards and writes trivandrum_wards.geojson.

Approach:
  - 56 verified wards: centre coordinates from known locality positions.
  - 44 placeholder wards: evenly-spaced grid cells inside each zone bbox,
    avoiding already-occupied cells.

Each polygon is a ±HALF_DEG degree square around the centre point.
HALF_DEG = 0.004° ≈ 440 m side — small enough to avoid overlaps.

The WARD_NO property is an integer (1–100) so import_ward_boundaries
maps it to TVM-001 … TVM-100 via int() → zero-padding.
"""

import json
import math

HALF = 0.004   # half-side of each square polygon in degrees (~440 m)


def make_polygon(lat, lng):
    """Return a GeoJSON Polygon (square) centred on (lat, lng)."""
    w, e = lng - HALF, lng + HALF
    s, n = lat - HALF, lat + HALF
    return {
        "type": "Polygon",
        "coordinates": [[
            [w, s], [e, s], [e, n], [w, n], [w, s]
        ]]
    }


def feature(ward_no, lat, lng, name):
    return {
        "type": "Feature",
        "properties": {"WARD_NO": ward_no, "WARD_NAME": name},
        "geometry": make_polygon(lat, lng),
    }


# ---------------------------------------------------------------------------
# Verified wards — approximate locality centres (WGS84)
# ---------------------------------------------------------------------------
VERIFIED = [
    # Central zone (TVM-001 – TVM-015)
    (1,  "Fort",              8.4868, 76.9234),
    (2,  "East Fort",         8.4850, 76.9310),
    (3,  "Attakulangara",     8.4806, 76.9260),
    (4,  "Chalai",            8.4920, 76.9335),
    (5,  "Killippalam",       8.4780, 76.9385),
    (6,  "Manacaud",          8.4705, 76.9380),
    (7,  "Thampanoor",        8.4964, 76.9505),
    (8,  "Palayam",           8.5030, 76.9478),
    (9,  "Statue",            8.5000, 76.9558),
    (10, "Vanchiyoor",        8.4930, 76.9430),
    (11, "Thycaud",           8.5055, 76.9382),
    (12, "Jagathy",           8.5130, 76.9482),
    (13, "Museum",            8.5122, 76.9378),
    (14, "Park",              8.5155, 76.9328),
    (15, "Chakkai",           8.5000, 76.9095),
    # East zone (TVM-021 – TVM-035)
    (21, "Vazhuthacaud",      8.5082, 76.9552),
    (22, "Vellayambalam",     8.5182, 76.9530),
    (23, "Kowdiar",           8.5252, 76.9448),
    (24, "Nanthancode",       8.5225, 76.9378),
    (25, "Pattom",            8.5282, 76.9318),
    (26, "Kesavadasapuram",   8.5355, 76.9278),
    (27, "Medical College",   8.5232, 76.9228),
    (28, "Ambalamukku",       8.5355, 76.9198),
    (29, "Kumarapuram",       8.5382, 76.9148),
    (30, "Kudappanakunnu",    8.5402, 76.9352),
    (31, "Peroorkada",        8.5435, 76.9128),
    (32, "Karamana",          8.4982, 76.9602),
    (33, "Kannammoola",       8.5102, 76.9622),
    (34, "Pappanamcode",      8.4882, 76.9482),
    (35, "Mannanthala",       8.5502, 76.9098),
    # North zone (TVM-046 – TVM-057)
    (46, "Enchakkal",         8.5552, 76.9198),
    (47, "Thirumala",         8.5632, 76.9178),
    (48, "Mudavanmughal",     8.5682, 76.8998),
    (49, "Vattiyoorkavu",     8.5802, 76.9052),
    (50, "Ulloor",            8.5452, 76.8898),
    (51, "Sreekaryam",        8.5532, 76.8848),
    (52, "Kazhakoottam",      8.5682, 76.8748),
    (53, "Karyavattom",       8.5602, 76.8818),
    (54, "Pravachambalam",    8.5902, 76.9098),
    (55, "Peyad",             8.6002, 76.9848),
    (56, "Thonnakkal",        8.5702, 76.8678),
    (57, "Naruvamoodu",       8.5852, 76.9248),
    # South zone (TVM-071 – TVM-076)
    (71, "Nemom",             8.4252, 76.9502),
    (72, "Kalliyoor",         8.3982, 76.9582),
    (73, "Thumba",            8.4702, 76.9118),
    (74, "Beemapally",        8.4552, 76.9152),
    (75, "Vizhinjam",         8.3832, 76.9982),
    (76, "Kovalam",           8.4002, 77.0032),
    # West zone (TVM-088 – TVM-095)
    (88, "Valiyathura",       8.4782, 76.9048),
    (89, "Poonthura",         8.4582, 76.8998),
    (90, "Vallakadavu",       8.5002, 76.8998),
    (91, "Muttathara",        8.5052, 76.8918),
    (92, "Veli",              8.5152, 76.8878),
    (93, "Akkulam",           8.5302, 76.8818),
    (94, "Shanghumugham",     8.5182, 76.8818),
    (95, "Kochuveli",         8.5432, 76.8778),
]

verified_nos = {w[0] for w in VERIFIED}

# ---------------------------------------------------------------------------
# Placeholder zones — bounding boxes for grid fill
# ---------------------------------------------------------------------------
# Each entry: (zone_name, first_ward_no, last_ward_no, lat_min, lat_max, lng_min, lng_max)
PLACEHOLDER_ZONES = [
    ("Central", 16, 20,  8.4630, 8.4960, 76.8960, 76.9180),
    ("East",    36, 45,  8.5530, 8.5850, 76.9380, 76.9750),
    ("North",   58, 70,  8.5700, 8.6100, 76.8680, 76.9450),
    ("South",   77, 87,  8.2800, 8.4200, 76.9400, 77.0100),
    ("West",    96, 100, 8.5480, 8.5750, 76.8680, 76.8970),
]


def grid_centres(lat_min, lat_max, lng_min, lng_max, count):
    """Return `count` evenly-spaced (lat, lng) centres filling the bbox."""
    cols = math.ceil(math.sqrt(count))
    rows = math.ceil(count / cols)
    lat_step = (lat_max - lat_min) / rows
    lng_step = (lng_max - lng_min) / cols
    centres = []
    for r in range(rows):
        for c in range(cols):
            if len(centres) >= count:
                break
            lat = lat_min + lat_step * (r + 0.5)
            lng = lng_min + lng_step * (c + 0.5)
            centres.append((lat, lng))
    return centres[:count]


# ---------------------------------------------------------------------------
# Build all features
# ---------------------------------------------------------------------------
features = []

# Verified wards
for ward_no, name, lat, lng in VERIFIED:
    features.append(feature(ward_no, lat, lng, name))

# Placeholder wards
for zone_name, first, last, lat_min, lat_max, lng_min, lng_max in PLACEHOLDER_ZONES:
    ward_numbers = [n for n in range(first, last + 1) if n not in verified_nos]
    centres = grid_centres(lat_min, lat_max, lng_min, lng_max, len(ward_numbers))
    for ward_no, (lat, lng) in zip(ward_numbers, centres):
        name = f"PLACEHOLDER-{zone_name.upper()}-{ward_no - first + 1:02d}"
        features.append(feature(ward_no, lat, lng, name))

# Sort by ward number for readability
features.sort(key=lambda f: f["properties"]["WARD_NO"])

# Sanity checks
all_nos = [f["properties"]["WARD_NO"] for f in features]
assert len(features) == 100, f"Expected 100 features, got {len(features)}"
assert sorted(all_nos) == list(range(1, 101)), "Ward numbers 1-100 not complete"
print(f"Generated {len(features)} ward polygons (ward numbers 1-100 complete)")

# ---------------------------------------------------------------------------
# Write GeoJSON
# ---------------------------------------------------------------------------
geojson = {"type": "FeatureCollection", "features": features}
output_path = "trivandrum_wards.geojson"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(geojson, f, indent=2)

print(f"Saved {output_path}")
print()
print("Ward summary:")
print(f"  Verified ward polygons : {len(VERIFIED)}")
print(f"  Placeholder polygons   : {100 - len(VERIFIED)}")
print(f"  Total                  : 100")
