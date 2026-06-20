import django, os, sys
sys.path.insert(0, r"C:\Users\91918\OneDrive\Desktop\civic grievance\backend")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from geolocation.service import detect_ward
from routing.models import RoutingRule

TESTS = [
    ("TVM-001 Fort (centre)",       8.4868,  76.9234, "KWA"),
    ("TVM-008 Palayam (centre)",    8.5030,  76.9478, "PWD"),
    ("TVM-050 Ulloor (centre)",     8.5452,  76.8898, "KSEB"),
    ("TVM-075 Vizhinjam (centre)",  8.3832,  76.9982, "PUBLIC_HEALTH"),
    ("TVM-092 Veli (centre)",       8.5152,  76.8878, "LSG"),
    ("Outside all wards",           9.0000,  77.5000, "KWA"),
]

print(f"\n{'Label':<35} {'Ward':^10} {'Category':^14} {'Department'}")
print("-" * 80)

all_pass = True
for label, lat, lng, cat in TESTS:
    ward = detect_ward(lat, lng)
    if ward is None:
        status = "OUTSIDE_BOUNDARY (expected)" if lat == 9.0 else "FAIL — no ward found"
        print(f"{label:<35} {'—':^10} {'—':^14} {status}")
        if lat != 9.0:
            all_pass = False
        continue
    try:
        rule = RoutingRule.objects.select_related("department", "jurisdiction").get(
            ward=ward, category=cat
        )
        print(f"{label:<35} {ward.code:^10} {cat:^14} {rule.department.name} / {rule.jurisdiction.name}  PASS")
    except RoutingRule.DoesNotExist:
        print(f"{label:<35} {ward.code:^10} {cat:^14} NO ROUTING RULE  FAIL")
        all_pass = False

print()
print("ALL PASS" if all_pass else "FAILURES DETECTED — review output above")
