import requests
import json
import sys

# Try broader bbox and both boundary tagging styles used in Kerala OSM
# south=8.15, west=76.75, north=8.75, east=77.15
query = (
    "[out:json][timeout:120];"
    "("
    '  relation["admin_level"="10"](8.15,76.75,8.75,77.15);'
    '  relation["boundary"="local_authority"](8.15,76.75,8.75,77.15);'
    ");"
    "out geom;"
)

SERVERS = [
    "https://overpass-api.de/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

print("Querying Overpass API...", flush=True)
resp = None
try:
    for server in SERVERS:
        print(f"  Trying {server} ...", flush=True)
        try:
            resp = requests.post(
                server,
                data={"data": query},
                headers={"Accept": "application/json"},
                timeout=180,
            )
            print(f"  Status: {resp.status_code}", flush=True)
            if resp.status_code == 200:
                break
            else:
                print(f"  Body: {resp.text[:300]}", flush=True)
        except Exception as e:
            print(f"  Failed: {e}", flush=True)
    if resp is None or resp.status_code != 200:
        print("All servers failed", flush=True)
        raise SystemExit(1)
    resp.raise_for_status()
    data = resp.json()
    elements = data.get("elements", [])
    print(f"Received {len(elements)} elements from Overpass", flush=True)

    # Print ref and name for each relation so we can see what was returned
    for el in elements:
        tags = el.get("tags", {})
        ref = tags.get("ref", "NO_REF")
        name = tags.get("name", "NO_NAME")
        print(f"  ref={ref:<5} name={name}")

    with open("osm_raw.json", "w", encoding="utf-8") as f:
        json.dump(data, f)
    print("Saved osm_raw.json", flush=True)

except Exception as e:
    print(f"ERROR: {e}", flush=True)
    sys.exit(1)
