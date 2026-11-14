"""
Step 4 - OpenStreetMap waterways (river, stream, canal, drain, ditch) near the district, extracted from a Geofabrik
Ghana .osm.pbf file. Used as a second, finer river network; its completeness was not checked in the field.

Usage
    python -I 04_osm_waterways.py <ghana-latest.osm.pbf> <tam_district.gpkg> <out.gpkg>
"""

import sys, osmium, geopandas as gpd
from shapely.geometry import LineString

PBF, DIST, OUT = sys.argv[1:4]
tam = gpd.read_file(DIST).to_crs(4326)
x0, y0, x1, y1 = tam.total_bounds
pad = 0.15
x0, y0, x1, y1 = x0 - pad, y0 - pad, x1 + pad, y1 + pad
KEEP = {"river", "stream", "canal", "drain", "ditch"}
rows = []


class H(osmium.SimpleHandler):
    def way(self, w):
        t = w.tags.get("waterway")
        if t not in KEEP:
            return
        try:
            pts = [(n.lon, n.lat) for n in w.nodes]
        except osmium.InvalidLocationError:
            return
        if len(pts) < 2:
            return
        if not any(x0 <= a <= x1 and y0 <= b <= y1 for a, b in pts):
            return
        rows.append(dict(osm_id=w.id, waterway=t, name=w.tags.get("name", ""), geometry=LineString(pts)))


H().apply_file(PBF, locations=True)
g = gpd.GeoDataFrame(rows, crs=4326).to_crs(32630)
g.to_file(OUT, driver="GPKG")
print(len(g), "waterways;", g.waterway.value_counts().to_dict())
print("named rivers:", sorted(set(g[g.waterway == "river"].name) - {""})[:30])
