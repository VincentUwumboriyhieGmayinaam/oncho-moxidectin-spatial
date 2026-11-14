"""
Step 3 - HydroRIVERS v1.0 (Lehner & Grill 2013) clipped to a box around the district (with a margin) and projected to
UTM zone 30N. HydroRIVERS is derived from 15 arc-second (about 460 m) elevation data and includes channels draining at
least 10 km2 or carrying at least 0.1 m3/s; each segment has a Strahler order (ORD_STRA). Order >= 3 is used as the
proxy for the larger perennial rivers where Simulium damnosum s.l. breeds.

Usage
    python -I 03_clip_hydrorivers.py <HydroRIVERS_v10_af.shp> <tam_district.gpkg> <out.gpkg>
"""

import sys, geopandas as gpd

SHP, DIST, OUT = sys.argv[1:4]
tam = gpd.read_file(DIST)
box = tam.to_crs(4326).total_bounds
pad = 0.15
r = gpd.read_file(SHP, bbox=(box[0] - pad, box[1] - pad, box[2] + pad, box[3] + pad))
print(len(r), "segments in padded box")
print(r.columns.tolist())
r = r.to_crs(32630)
inside = r[r.intersects(tam.geometry.iloc[0].buffer(5000))]
print(len(inside), "segments within 5 km of district")
print(
    inside[["ORD_STRA", "ORD_FLOW", "DIS_AV_CMS", "LENGTH_KM", "UPLAND_SKM"]].describe().round(2).to_string()
)
print(inside.ORD_STRA.value_counts().sort_index().to_dict())
r.to_file(OUT, driver="GPKG")
