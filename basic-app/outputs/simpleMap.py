import geopandas as gpd
parks_gdf = gpd.read_file(r'basic-app/data/auckland_parks.geojson')

# First, try a direct merge to see what matches
merged = park_summary.merge(
    parks_gdf, 
    left_on='park_name', 
    right_on='SITEDESCRIPTION', 
    how='left',
    indicator=True
)

# See which parks didn't match
unmatched = merged[merged['_merge'] == 'left_only']['park_name'].unique()
print(f"Unmatched parks ({len(unmatched)}):")
print(unmatched)