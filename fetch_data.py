"""
fetch_data.py — Wachusett Reservoir data pipeline

Downloads all map layers from public sources and saves to data/ as GeoJSON.
Run once to populate; re-run any time to refresh.

Input:  MassGIS ArcGIS FeatureServer REST APIs, Digital Commonwealth JSON API
Output: data/watershed.geojson, data/bathymetry.geojson,
        data/trails.geojson, data/fishing_gates.geojson,
        data/historical_photos.geojson
CRS:    WGS84 (EPSG:4326) throughout — ArcGIS REST reprojects on request
        via outSR=4326. USGS gauge data is fetched live in the browser.
Filter: bathymetry and trails are multi-reservoir DCR datasets; a server-side
        ArcGIS envelope filter restricts results to the Wachusett area only.

Usage:
    pip install requests
    python fetch_data.py
    python -m http.server 8000   # then open http://localhost:8000

Note: If MassGIS URLs below return 4xx errors, find current endpoints at
      https://massgis.maps.arcgis.com → search "DCR DWSP" → open dataset
      → Details → View API → copy the FeatureServer URL.
"""

import json
import sys
import requests
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────────────────────
DATA_DIR = Path("data")

# MassGIS ArcGIS Online FeatureServer URLs — DCR DWSP public datasets.
# Each tuple is (service_url, WHERE clause).
# Org ID 7iJyYTjCtKsZS1LR = DCR DWSP ArcGIS Online org (mass-eoeea).
MASSGIS_LAYERS = {
    "watershed": (
        "https://services1.arcgis.com/7iJyYTjCtKsZS1LR/arcgis/rest/services"
        "/QWWS_Watershed_Boundaries/FeatureServer/0",
        "NAME = 'Wachusett'",  # NAME field confirmed from layer schema
    ),
    "bathymetry": (
        "https://services1.arcgis.com/7iJyYTjCtKsZS1LR/arcgis/rest/services"
        "/Wachusett_Reservoir_Bathymetry_10_foot_Contours/FeatureServer/0",
        "1=1",  # Wachusett-specific dataset — no attribute filter needed
    ),
    "trails": (
        "https://services1.arcgis.com/7iJyYTjCtKsZS1LR/arcgis/rest/services"
        "/DCR-DWSP_Trails_and_Roads_Public_View/FeatureServer/0",
        "1=1",  # multi-watershed layer; Wachusett bbox filter applied in main
    ),
    "fishing_gates": (
        "https://services1.arcgis.com/7iJyYTjCtKsZS1LR/arcgis/rest/services"
        "/DWSP_QWWS_Gate_Inventory_(Public_View)/FeatureServer/0",
        "1=1",  # multi-watershed layer; Wachusett bbox filter applied in main
    ),
}

# Curated historical photos: manually selected from the Massachusetts Metropolitan
# Water Works Photograph Collection (Digital Commonwealth / Massachusetts Archives).
# The DC API does not expose geographic_center_geospatial for this collection, so
# coordinates are assigned manually from photo titles and 1898 USGS survey data.
# All points are in WGS84 (EPSG:4326); [longitude, latitude] per GeoJSON spec.
# Old West Boylston (items marked *) is now submerged under the reservoir.
DC_BASE_ITEM  = "https://www.digitalcommonwealth.org/search"
# Thumbnail URL pattern confirmed: blob storage serves image_thumbnail_300.jpg
DC_THUMB_BASE = "https://bpldcassets.blob.core.windows.net/derivatives/images"

HISTORICAL_PHOTOS = [
    # ── Old Stone Church (First Liberal Congregational Society) ─────────────────
    {
        "id":       "commonwealth:qb98mw61n",
        "image":    "commonwealth:qb98mw62x",
        "title":    "Old Stone Church (Congregational Society), from the northwest",
        "date":     "1898-10-17",
        "desc":     "Church building at corner of Central & Worcester Sts, West Boylston; "
                    "documented by Water Board photographer Charles W. Tarr before demolition. "
                    "Now submerged under the reservoir.",
        "lng": -71.790, "lat": 42.378,   # * old West Boylston center, now submerged
        "coord_note": "Approx. corner of Central & Worcester Sts per photo title; "
                      "area now beneath reservoir surface",
    },
    {
        "id":       "commonwealth:qb98mw59m",
        "image":    "commonwealth:qb98mw60c",
        "title":    "Old Stone Church (Congregational Society), from the southeast",
        "date":     "1898-10-17",
        "desc":     "Opposite view of the same stone church building; second of two angles "
                    "photographed on the same day for the Metropolitan Water Board real-estate survey.",
        "lng": -71.790, "lat": 42.378,   # * same intersection as above
        "coord_note": "Approx. corner of Central & Worcester Sts per photo title",
    },
    # ── Other West Boylston churches (flood-zone survey) ───────────────────────
    {
        "id":       "commonwealth:pg15bn003",
        "image":    "commonwealth:pg15bn01c",
        "title":    "First Baptist Church, West Boylston",
        "date":     "1897-10-16",
        "desc":     "Baptist church in old West Boylston town center, photographed as part "
                    "of the Metropolitan Water Board property survey. Now submerged.",
        "lng": -71.786, "lat": 42.376,   # * old West Boylston, ~150 m NE of Congregational
        "coord_note": "Old West Boylston town area; DC gives town-level centroid only",
    },
    {
        "id":       "commonwealth:pg15bn46q",
        "image":    "commonwealth:pg15bn470",
        "title":    "Catholic Church, West Boylston",
        "date":     "1898-05-20",
        "desc":     "Catholic church building in old West Boylston, part of the reservoir "
                    "real-estate acquisition survey.",
        "lng": -71.788, "lat": 42.374,   # * old West Boylston, south of Congregational
        "coord_note": "Old West Boylston town area; DC gives town-level centroid only",
    },
    # ── Dam construction ────────────────────────────────────────────────────────
    {
        "id":       "commonwealth:ft848x07c",
        "image":    "commonwealth:ft848x08n",
        "title":    "Wachusett Dam — first stone laid",
        "date":     "1901-06-05",
        "desc":     "Construction milestone: first masonry stone placed at the dam site. "
                    "Photographed by George P. Goodman for the Metropolitan Water and "
                    "Sewerage Board.",
        "lng": -71.714, "lat": 42.423,   # Wachusett Dam crest, Clinton MA
        "coord_note": "Wachusett Dam; coordinates from USGS NHD dam feature",
    },
    {
        "id":       "commonwealth:ht24x6102",
        "image":    "commonwealth:ht24x611b",
        "title":    "Construction railroad cut near Sandy Pond, from the north",
        "date":     "1898-06-16",
        "desc":     "Railroad grading cut used to haul dam construction materials; "
                    "photographed near Sandy Pond in Clinton, east of the reservoir basin.",
        "lng": -71.703, "lat": 42.418,   # Sandy Pond vicinity, Clinton MA
        "coord_note": "Approx. Sandy Pond area per photo title; Clinton MA",
    },
    # ── Earthworks ──────────────────────────────────────────────────────────────
    {
        "id":       "commonwealth:5m60r593v",
        "image":    "commonwealth:5m60r5944",
        "title":    "North Dike construction",
        "date":     "1899-01-01",          # dated ca. 1899 in collection
        "desc":     "Earthwork construction of the North Dike, which closes the northern "
                    "gap in the reservoir rim between Clinton and Sterling.",
        "lng": -71.712, "lat": 42.441,   # North Dike, Clinton / Sterling border
        "coord_note": "North Dike crest; approximate from reservoir geometry",
    },
    # ── West Boylston Arch (Quinapoxet River) ───────────────────────────────────
    {
        "id":       "commonwealth:9p290987v",
        "image":    "commonwealth:9p2909884",
        "title":    "Building the West Boylston Arch",
        "date":     "1904-09-18",
        "desc":     "Stone arch under construction over the Quinapoxet River where it "
                    "enters the reservoir; photographed by Charles W. Tarr.",
        "lng": -71.780, "lat": 42.381,   # Quinapoxet River inlet to reservoir, West Boylston
        "coord_note": "Quinapoxet River arch, West Boylston; approx. from reservoir shoreline",
    },
    {
        "id":       "commonwealth:z316q389r",
        "image":    "commonwealth:z316q390h",
        "title":    "West Boylston Arch, completed",
        "date":     "1904-12-02",
        "desc":     "Completed stone arch carrying the former road over the Quinapoxet River "
                    "at the reservoir inlet — still partially visible above waterline today.",
        "lng": -71.780, "lat": 42.381,   # same structure as above
        "coord_note": "Quinapoxet River arch, West Boylston",
    },
]

# Wachusett Reservoir approximate bounding box, WGS84 (EPSG:4326).
# x = longitude, y = latitude — per OGC axis order for ArcGIS envelopes.
# Used as a server-side geometry filter for multi-reservoir DCR layers.
WACHUSETT_BBOX = {
    "xmin": -71.85,
    "ymin": 42.37,
    "xmax": -71.70,
    "ymax": 42.48,
}

# ── Fetch helpers ──────────────────────────────────────────────────────────────
def build_envelope_params(bbox: dict) -> dict:
    """Return ArcGIS REST params for a server-side envelope (bbox) spatial filter."""
    return {
        "geometry":     f"{bbox['xmin']},{bbox['ymin']},{bbox['xmax']},{bbox['ymax']}",
        "geometryType": "esriGeometryEnvelope",
        "spatialRel":   "esriSpatialRelIntersects",
        "inSR":         "4326",  # bbox CRS — WGS84 to match outSR
    }


def probe_layer_fields(service_url: str) -> list[str]:
    """Return field names from ArcGIS layer metadata. Returns [] on any error."""
    try:
        r = requests.get(service_url, params={"f": "json"}, timeout=15)
        r.raise_for_status()
        return [f["name"] for f in r.json().get("fields", [])]
    except (requests.RequestException, KeyError, ValueError):
        return []


def fetch_arcgis_layer(
    name: str,
    service_url: str,
    where: str = "1=1",
    extra_params: dict | None = None,
) -> bool:
    """
    Query a MassGIS ArcGIS FeatureServer layer and save as WGS84 GeoJSON.
    Returns True on success, False on failure (so caller can report progress).
    Pass extra_params to apply additional ArcGIS query parameters (e.g. a
    geometry envelope filter) on top of the WHERE clause.
    """
    params = {
        "where":             where,
        "outFields":         "*",
        "f":                 "geojson",
        "outSR":             "4326",   # ArcGIS reprojects on the fly to WGS84
        "resultRecordCount": 2000,
    }
    if extra_params:
        params.update(extra_params)
    print(f"  {name} ...", end=" ", flush=True)

    try:
        r = requests.get(f"{service_url}/query", params=params, timeout=30)
        r.raise_for_status()
    except requests.RequestException as exc:
        print(f"FAILED\n    {exc}")
        print(f"    -> Verify URL at massgis.maps.arcgis.com: {service_url}")
        return False

    data = r.json()
    out_path = DATA_DIR / f"{name}.geojson"
    out_path.write_text(r.text, encoding="utf-8")
    count = len(data.get("features", []))

    if count == 0:
        # Empty result usually means the WHERE clause field name is wrong
        print(f"0 features — check WHERE clause field name for {name}")
    else:
        print(f"{count} features -> {out_path}")

    if data.get("exceededTransferLimit"):
        print(f"  WARNING: {name} hit the 2000-feature limit — results may be truncated.")

    return count > 0


def build_curated_photo_geojson() -> None:
    """
    Write data/historical_photos.geojson from the HISTORICAL_PHOTOS curated list.

    The Digital Commonwealth API does not expose geographic_center_geospatial for
    the Metropolitan Water Works Photograph Collection, so coordinates are assigned
    manually based on photo titles and 1898 USGS survey data. Each feature records
    its coord_note in properties so the provenance is clear.
    """
    print("  historical_photos ...", end=" ", flush=True)

    features = []
    for photo in HISTORICAL_PHOTOS:
        thumb_url = f"{DC_THUMB_BASE}/{photo['image']}/image_thumbnail_300.jpg"
        item_url  = f"{DC_BASE_ITEM}/{photo['id']}"
        features.append({
            "type": "Feature",
            "geometry": {
                "type":        "Point",
                "coordinates": [photo["lng"], photo["lat"]],  # GeoJSON: [longitude, latitude]
            },
            "properties": {
                "title":      photo["title"],
                "date":       photo["date"],
                "desc":       photo["desc"],
                "thumb":      thumb_url,
                "item_url":   item_url,
                "coord_note": photo["coord_note"],
            },
        })

    out_path = DATA_DIR / "historical_photos.geojson"
    out_path.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, indent=2),
        encoding="utf-8",
    )
    print(f"{len(features)} curated photos -> {out_path}")


# ── Main ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    DATA_DIR.mkdir(exist_ok=True)
    any_failed = False

    # Layers that span multiple DCR reservoirs and must be spatially clipped
    # to the Wachusett area. Watershed uses an attribute WHERE; bathymetry is
    # already a Wachusett-specific dataset and needs no spatial filter.
    SPATIALLY_FILTERED = {"trails", "fishing_gates"}
    wachusett_envelope = build_envelope_params(WACHUSETT_BBOX)

    # Probe field schemas to check whether an attribute WHERE clause could
    # supplement the bbox filter (informational only — does not block fetching).
    print("Probing layer schemas:")
    for layer_name in SPATIALLY_FILTERED:
        url, _ = MASSGIS_LAYERS[layer_name]
        fields = probe_layer_fields(url)
        hits = [
            f for f in fields
            if any(kw in f.upper() for kw in ("RESERVOIR", "WATERSHED", "BASIN"))
        ]
        if hits:
            print(f"  {layer_name}: candidate attribute fields found: {hits}")
            print(f"    -> Consider adding a WHERE clause in MASSGIS_LAYERS.")
        else:
            print(f"  {layer_name}: no watershed attribute field — bbox filter only.")

    print("\nFetching MassGIS layers:")
    for layer_name, (url, where) in MASSGIS_LAYERS.items():
        extra = wachusett_envelope if layer_name in SPATIALLY_FILTERED else None
        ok = fetch_arcgis_layer(layer_name, url, where, extra_params=extra)
        if not ok:
            any_failed = True

    print("\nBuilding curated historical photo layer:")
    build_curated_photo_geojson()

    print("\nDone.")
    if any_failed:
        print("Some layers failed — see messages above.")
        print("The map will still load; failed layers will simply be empty.")
    print("\nServe the project with:")
    print("  python -m http.server 8000")
    print("  Open: http://localhost:8000")
