import geopandas as gpd
parks_gdf = gpd.read_file(r'basic-app/data/auckland_parks.geojson')

# See what it looks like
print(parks_gdf.head())

# Check column names (find the park name column!)
print(parks_gdf.columns)

# Quick plot to see the shapes
#parks_gdf.plot()

print(parks_gdf['DESCRIPTION'])

