import sys, geopandas as gpd
SHP, DIST, OUT = sys.argv[1:4]
tam = gpd.read_file(DIST)
box = tam.to_crs(4326).total_bounds
pad = 0.15
r = gpd.read_file(SHP, bbox=(box[0]-pad, box[1]-pad, box[2]+pad, box[3]+pad))
print(len(r), 'segments in padded box'); print(r.columns.tolist())
r = r.to_crs(32630)
inside = r[r.intersects(tam.geometry.iloc[0].buffer(5000))]
print(len(inside), 'segments within 5 km of district')
print(inside[['ORD_STRA','ORD_FLOW','DIS_AV_CMS','LENGTH_KM','UPLAND_SKM']].describe().round(2).to_string())
print(inside.ORD_STRA.value_counts().sort_index().to_dict())
r.to_file(OUT, driver='GPKG')
