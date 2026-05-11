# Wachusett Reservoir Explorer

An interactive web map of the Wachusett Reservoir (Clinton, MA) built entirely from open public data. Features bathymetric depth mapping, DCR access gate navigation, hiking trails, historical photographs, and live USGS stream gauge readings.

---

## Table of Contents

1. [What This Map Shows](#what-this-map-shows)
2. [Project Structure](#project-structure)
3. [Data Sources](#data-sources)
4. [Quick Start (Local)](#quick-start-local)
5. [Refreshing the Data](#refreshing-the-data)
6. [Gate Numbering System](#gate-numbering-system)
7. [Layer Details](#layer-details)
8. [Technical Notes](#technical-notes)
9. [Attribution](#attribution)

---

## What This Map Shows

| Layer | What you see |
|---|---|
| **Watershed boundary** | Dashed blue outline of the Wachusett watershed |
| **Bathymetry** | 10-ft depth contour bands, light → dark blue (0–120 ft) |
| **Trails & Roads** | DCR DWSP permitted access routes around the reservoir |
| **Gates** | All 125 DCR access gates with numbers, town, ADA status, and allowed uses |
| **Historic Photos** | 9 curated photographs (1897–1904) from the Metropolitan Water Works collection |
| **USGS Gauges** | Live stream discharge and stage readings, refreshed on every page load |

**Key feature for locals:** Every gate is labeled on the map (e.g. "Gate 30", "Gate WB15") and searchable by number. Click any gate dot for access conditions, ADA info, and signage rules.

---

## Project Structure

```
wachusett-map/
│
├── index.html          ← The entire map application (single HTML file)
├── fetch_data.py       ← Python pipeline — downloads all GeoJSON from public APIs
├── start.bat           ← Windows launcher (double-click to open map locally)
├── .gitignore
├── README.md
│
└── data/               ← Pre-generated GeoJSON (committed to repo for GitHub Pages)
    ├── watershed.geojson       — Wachusett watershed boundary polygon
    ├── bathymetry.geojson      — 12 depth contour band polygons (10-ft intervals)
    ├── trails.geojson          — 355 trail and road segments
    ├── fishing_gates.geojson   — 125 DCR access gate points
    └── historical_photos.geojson — 9 curated historical photo locations
```

---

## Data Sources

### MassGIS / DCR–DWSP (Massachusetts GeoServices)

All spatial layers are fetched from the DCR Division of Water Supply Protection's public ArcGIS Online organization (`services1.arcgis.com/7iJyYTjCtKsZS1LR`).

| Layer | Service Name | Filter Applied |
|---|---|---|
| Watershed boundary | `QWWS_Watershed_Boundaries` | `NAME = 'Wachusett'` |
| Bathymetry | `Wachusett_Reservoir_Bathymetry_10_foot_Contours` | None (Wachusett-only dataset) |
| Trails & Roads | `DCR-DWSP_Trails_and_Roads_Public_View` | Wachusett bounding box |
| Fishing / Access Gates | `DWSP_QWWS_Gate_Inventory_(Public_View)` | Wachusett bounding box |

**Bounding box used for spatial filtering:**
```
xmin: -71.85  ymin: 42.37  xmax: -71.70  ymax: 42.48  (WGS84)
```

### Historical Photographs

9 photographs manually curated from the **Massachusetts Metropolitan Water Works Photograph Collection** (Massachusetts Archives / Digital Commonwealth). Coordinates are manually assigned based on photo titles and 1898 USGS survey data — the old West Boylston town center photographed in 1897–1898 is now submerged under the reservoir.

| Photo | Date | Subject |
|---|---|---|
| Old Stone Church (NW view) | 1898-10-17 | Congregational church at Central & Worcester Sts |
| Old Stone Church (SE view) | 1898-10-17 | Opposite angle of same stone building |
| First Baptist Church | 1897-10-16 | Baptist church, old West Boylston (now submerged) |
| Catholic Church | 1898-05-20 | Catholic church, old West Boylston (now submerged) |
| Wachusett Dam — first stone | 1901-06-05 | Construction milestone at the dam, Clinton |
| Railroad cut near Sandy Pond | 1898-06-16 | Construction railroad, Clinton |
| North Dike construction | ca. 1899 | North Dike earthwork, Clinton/Sterling border |
| Building the West Boylston Arch | 1904-09-18 | Stone arch over Quinapoxet River |
| West Boylston Arch, completed | 1904-12-02 | Completed arch (still partially visible today) |

### USGS NWIS (Live Gauges)

Fetched live in the browser on every page load via the USGS National Water Information System instantaneous values API (CORS-enabled, no API key required).

| Site | Station | Parameters |
|---|---|---|
| `01095220` | Stillwater River at Sterling, MA | Discharge (cfs), Stage (ft) |
| `01095434` | Quinapoxet River near Holden, MA | Discharge (cfs), Stage (ft) |

---

## Quick Start (Local)

### Prerequisites

- Python 3.10+ with `requests` installed:
  ```
  pip install requests
  ```
- A modern browser (Chrome, Firefox, Edge, Safari)

### Step 1 — Download the data

Run the pipeline once to populate the `data/` folder:

```bash
python fetch_data.py
```

Expected output:
```
Probing layer schemas:
  trails: no watershed attribute field — bbox filter only.
  fishing_gates: candidate attribute fields found: ['Watershed']

Fetching MassGIS layers:
  watershed ... 1 features -> data\watershed.geojson
  bathymetry ... 12 features -> data\bathymetry.geojson
  trails ... 355 features -> data\trails.geojson
  fishing_gates ... 125 features -> data\fishing_gates.geojson

Building curated historical photo layer:
  historical_photos ... 9 curated photos -> data\historical_photos.geojson
```

### Step 2 — Serve the map

**Windows — double-click `start.bat`**

Or run manually:
```bash
python -m http.server 8000
```

Then open **`http://localhost:8000`** in your browser.

> **Important:** Never open `index.html` directly (via `file://`). Browsers block `fetch()` requests on the file:// protocol, so the GeoJSON layers and USGS gauge data won't load. Always use the HTTP server.

---

## Refreshing the Data

The GeoJSON files in `data/` are static snapshots. To pull the latest data from MassGIS (e.g. updated gate inventory, new trails):

```bash
python fetch_data.py
```

This overwrites all files in `data/`. USGS gauge data is always live — it refreshes automatically on every page load.

---

## Gate Numbering System

The reservoir is ringed by 125 DCR access gates, each with a unique identifier. Local users navigate by gate number — "Gate 22 for the best views" is common local knowledge.

| Prefix | Area |
|---|---|
| Plain numbers (`4`, `6`, `8`, `26` …`39`) | Clinton and Sterling (dam side) |
| `WB` (e.g. `WB15`, `WB35A`) | West Boylston |
| `S` (e.g. `S1`, `S22`, `S35`) | Sterling (north shore) |
| `H` (e.g. `H6`, `H21`) | Holden |
| `B` (e.g. `B4`, `B7`) | Boylston |
| `P` (e.g. `P6`, `P7`) | Princeton |
| Named | North Dike 1–3, I-190 Quinapoxet 1–2, 77 Lancaster St |

### Using the Gate Search

Type a gate number in the **Find a Gate** panel (e.g. `22`, `WB15`, `S8`) and press **Go** or **Enter**. The map flies to that gate and opens a popup showing:
- Town and ADA accessibility
- Gate and sign condition
- Allowed/prohibited uses (fishing, dogs, drones, parking)

You can also use the **pick from list** dropdown, which lists all 125 gates sorted numerically then alphabetically.

### Gate Labels on the Map

Gate labels are linked to the **Trails & Roads** toggle — turning trails on automatically shows all gate numbers as green labels on the map, giving hikers a navigation overlay in a single toggle.

---

## Layer Details

### Bathymetry

- **Source:** `Wachusett_Reservoir_Bathymetry_10_foot_Contours` (DCR DWSP)
- **Field used for colour ramp:** `MaxDisplayContour` (deep edge of each 10-ft band)
- **Depth range:** 0 – 120 ft
- **Colour scale:** `#deeef8` (near-white, shallow) → `#4292c6` (mid-blue, ~60 ft) → `#08306b` (navy, 120 ft)
- **Click any contour** to see the depth band label (e.g. "90 – 100 feet")

### Trails & Roads

- **Source:** `DCR-DWSP_Trails_and_Roads_Public_View`
- **355 features** clipped to the Wachusett bounding box
- Click any trail segment for name, surface type, and trail type
- Toggle is linked to gate labels — turning trails on/off also shows/hides gate numbers

### Historical Photos

- **9 hand-curated features** from the Metropolitan Water Works Photograph Collection (1897–1904)
- Coordinates are manually assigned — the Digital Commonwealth API does not expose `geographic_center_geospatial` for this collection
- Each feature records a `coord_note` explaining the coordinate source
- Click any amber dot to open the photo modal with the full image thumbnail and a link to the Digital Commonwealth record
- Photos of the old West Boylston churches are placed at their original pre-flooding locations, now beneath the reservoir surface

---

## Technical Notes

### Why `file://` doesn't work

Browsers enforce the **Same-Origin Policy** for `fetch()` requests. When `index.html` is opened as `file:///...`, every `fetch()` to a relative path (`data/watershed.geojson`) is blocked as a cross-origin request. The USGS NWIS API call also fails. Always serve the project through an HTTP server.

### CRS and coordinate order

All data is in **WGS84 (EPSG:4326)** throughout.

- **GeoJSON spec:** `[longitude, latitude]`
- **MapLibre GL JS:** `[longitude, latitude]` (same as GeoJSON)
- **Leaflet (not used here):** `[latitude, longitude]` — opposite order

Comments in `index.html` flag every coordinate array to prevent axis-flip bugs.

### MassGIS endpoint discovery

The old MassGIS proxy (`gisprpxy.itd.state.ma.us`) has a certificate mismatch and is no longer usable. All service URLs now point directly to the DCR DWSP ArcGIS Online organisation:

```
https://services1.arcgis.com/7iJyYTjCtKsZS1LR/arcgis/rest/services/
```

If a layer URL returns a 4xx error in the future, find the current endpoint at:
1. Go to [mass-eoeea.maps.arcgis.com](https://mass-eoeea.maps.arcgis.com)
2. Search for `DCR DWSP <layer name>`
3. Open the Feature Service item → copy the REST URL

### Bounding box spatial filter

Multi-reservoir DCR layers (trails, gates) are filtered server-side using an ArcGIS REST envelope query:

```python
{
  "geometry":     "-71.85,42.37,-71.70,42.48",
  "geometryType": "esriGeometryEnvelope",
  "spatialRel":   "esriSpatialRelIntersects",
  "inSR":         "4326"
}
```

A schema probe (`probe_layer_fields`) runs before each filtered download and logs any attribute field that could supplement the bbox filter with a WHERE clause.

---

## Attribution

| Data | Source | License |
|---|---|---|
| Watershed boundary, bathymetry, trails, gates | MassGIS / DCR–DWSP | Public domain |
| Historical photographs | Massachusetts Archives / Digital Commonwealth | No known copyright restrictions |
| Base map tiles | CartoDB Voyager via MapLibre GL JS | © CARTO, © OpenStreetMap contributors |
| Stream gauge data | USGS National Water Information System | Public domain |
| Map engine | [MapLibre GL JS](https://maplibre.org/) | BSD-3-Clause |

---

*Built with Python, MapLibre GL JS, and open Massachusetts public data.*
