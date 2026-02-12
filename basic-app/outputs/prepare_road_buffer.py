import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

# -----------------------
# Load bins
# -----------------------
df = pd.read_csv("basic-app\data\parks_cleaned_dups_removed_final.csv")

gdf_bins = gpd.GeoDataFrame(
    df,
    geometry=gpd.points_from_xy(df.lon, df.lat),
    crs="EPSG:4326"
)

# -----------------------
# Load roads
# -----------------------
roads = gpd.read_file("basic-app\data\Road_Centrelines.geojson")

# -----------------------
# Project to NZTM (meters)
# -----------------------
gdf_bins = gdf_bins.to_crs(epsg=2193)
roads = roads.to_crs(epsg=2193)

# -----------------------
# Buffer roads 500m
# -----------------------
road_buffer = roads.buffer(100)
road_union = road_buffer.unary_union

# -----------------------
# Mark bins within buffer
# -----------------------
gdf_bins["near_road_100m"] = gdf_bins.geometry.within(road_union)

# -----------------------
# Convert back to lat/lon
# -----------------------
gdf_bins = gdf_bins.to_crs(epsg=4326)

# Drop geometry before saving
final_df = pd.DataFrame(gdf_bins.drop(columns="geometry"))

# -----------------------
# Save updated dataset
# -----------------------
final_df.to_csv(
    "basic-app\data\parks_cleaned_dups_removed_final.csv",
    index=False
)

print("Done! near_road_100m column added.")
