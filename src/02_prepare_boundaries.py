"""
Step 2 - Boundaries and settlements for Paper 5.

Reads the national district and settlement shapefiles, keeps Twifo Atti-Morkwa District and its neighbours, and
projects everything to UTM zone 30N (EPSG:32630) so that distances are in metres. Survey communities are matched by
name to the national settlement file and their centroid is the median of household coordinates.

Usage
    python -I 02_prepare_boundaries.py <district_folder> <paper5_spatial.csv> <gis_output_folder>
"""

import sys, re, difflib
import geopandas as gpd, pandas as pd, numpy as np

SRC, DATA, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
dist = gpd.read_file(f"{SRC}/New_District.shp")
tam = dist[dist.name == "Twifo Atti Morkwa District"].to_crs(32630)
tam.to_file(f"{OUT}/tam_district.gpkg", driver="GPKG")
nbr = dist.to_crs(32630)
nbr = nbr[nbr.touches(tam.geometry.iloc[0]) | nbr.intersects(tam.geometry.iloc[0].buffer(2000))]
nbr.to_file(f"{OUT}/neighbour_districts.gpkg", driver="GPKG")
print("district area km2", round(tam.area.iloc[0] / 1e6, 1), "| neighbours:", len(nbr) - 1)
com = gpd.read_file(f"{SRC}/Community.shp")
cd = com[com.DISTRICT.str.contains("TWIFO ATI", na=False)].copy()
inside = cd[cd.within(tam.geometry.iloc[0].buffer(500))]
print("national community points labelled TAM:", len(cd), "| within district polygon:", len(inside))
cd.to_file(f"{OUT}/tam_communities_all.gpkg", driver="GPKG")
# survey communities: median of cleaned GPS
s = pd.read_csv(DATA)
s = s[s.gps_lat.notna() & (s.gps_flag != 5)]
med = s.groupby("community_name")[["gps_lon", "gps_lat"]].median()
sv = gpd.GeoDataFrame(med, geometry=gpd.points_from_xy(med.gps_lon, med.gps_lat), crs=4326).to_crs(32630)


def norm(x):
    return re.sub(r"[^a-z]", "", x.lower())


rows = []
for name, r in sv.iterrows():
    cand = cd.copy()
    cand["d_km"] = cand.distance(r.geometry) / 1000
    near = cand.nsmallest(5, "d_km")
    ratio = near.Community.map(
        lambda c: difflib.SequenceMatcher(None, norm(name.split("/")[0]), norm(str(c))).ratio()
    )
    best = near.assign(sim=ratio).sort_values(["sim", "d_km"], ascending=[False, True]).iloc[0]
    rows.append(
        dict(
            survey_community=name,
            matched=best.Community,
            sim=round(best.sim, 2),
            dist_km=round(best.d_km, 2),
            nearest=near.iloc[0].Community,
            nearest_km=round(near.iloc[0].d_km, 2),
            inside_district=bool(tam.geometry.iloc[0].buffer(500).contains(r.geometry)),
        )
    )
m = pd.DataFrame(rows)
print(m.to_string())
m.to_csv(f"{OUT}/community_matching.csv", index=False)
sv.to_file(f"{OUT}/survey_community_centroids.gpkg", driver="GPKG")
