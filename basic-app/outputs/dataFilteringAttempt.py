import pandas as pd
import geopandas as gpd
import folium


raw_data = pd.read_csv("~/OneDrive/Documents/SRS/parks_cleaned_dups_removed_final.csv")
#print(raw_data.columns)

# Group by park and count the number of rows (bins)
bins_per_park = raw_data.groupby('park_name').size().reset_index(name='total_bins')
#print(bins_per_park)

park_summary = raw_data.groupby('park_name').size().reset_index(name = 'total_bins')

raw_data['has_recycling'] = raw_data['key_features'].str.contains('recycling', case=False, na=False)
raw_data['has_general'] = ~raw_data['has_recycling']

park_summary = raw_data.groupby('park_name').agg(
    total_bins=('park_name', 'size'),
    bins_recycling=('has_recycling', 'sum'),
    bins_general=('has_general', 'sum')
).reset_index()

park_summary.to_csv(r'basic-app\outputs\park_bin_summaryv1.csv', index=False)
#print(park_summary.head())

#----------------- City Summary Creation ----------
number_of_parks = len(park_summary)
mean_bins = park_summary['total_bins'].mean()
median_bins = park_summary['total_bins'].median()
min_bins = park_summary['total_bins'].min()
max_bins = park_summary['total_bins'].max()


# Note - this data does not yet include density information
city_summary = pd.DataFrame({
    'metric': ['number_of_parks', 'mean_bins_per_park', 'median_bins_per_park', 'min_bins_per_park', 'max_bins_per_park'],
    'value': [number_of_parks, mean_bins, median_bins, min_bins, max_bins]
})

park_summary['bin_range'] = pd.cut(
    park_summary['total_bins'],
    bins=[0, 1, 3, 6, 11, 16, float('inf')],
    labels=['0 bins', '1-2 bins', '3-5 bins', '6-10 bins', '11-15 bins', '16+ bins'],
    right=False
)

distribution = park_summary['bin_range'].value_counts().sort_index().reset_index()
distribution.columns = ['bin_range', 'number_of_parks']

# Save the summary statistics
city_summary.to_csv(r'basic-app\outputs\citywide_bin_summary.csv', index=False)

# Save the distribution
distribution.to_csv(r'basic-app\outputs\citywide_bin_distribution.csv', index=False)

# Join the two
blank_row = pd.DataFrame({'metric': [''], 'value': ['']})
combined = pd.concat([city_summary, blank_row, distribution.rename(columns={'bin_range': 'metric', 'number_of_parks': 'value'})], ignore_index=True)
combined.to_csv(r'basic-app\outputs\citywide_bin_summaryv2.csv', index=False)





#----------------------- Simple python map


parks_gdf = gpd.read_file(r'basic-app/data/auckland_parks.geojson')

#direct merge
merged = park_summary.merge(
    parks_gdf, 
    left_on='park_name', 
    right_on='SITEDESCRIPTION', 
    how='left',
    indicator=True
)


#name mapping dictionary
name_mapping = {
    "Barry's Point Reserve": 'Barrys Point Reserve',
    'Bastian Point/Whenua Rangatira': 'Whenua Rangatira',
    'Chamberlain Park ': 'Chamberlain Park',
    "Cox's Bay Reserve": 'Coxs Bay Reserve',
    'Lemington Reserve': 'Westmere Park',
    'Mount Wellington War Memorial Park': 'Mt Wellington War Memorial Reserve',
    'Narrow Neck': 'Woodall Park',
    'Waiatarua Reserve': 'Waiatarua Reserve (Remuera)',
    'Waitemata Golf Club': 'Alison Park',
    'Western Springs Lakeside Park': 'Western Springs Lakeside'
}

park_summary['park_name_clean'] = park_summary['park_name'].replace(name_mapping)

merged = gpd.GeoDataFrame(
    park_summary.merge(
        parks_gdf,
        left_on='park_name_clean',
        right_on='SITEDESCRIPTION',
        how='left'
    ),
    geometry='geometry'
)

center_lat = -36.8485
center_lon = 174.7633

base_map = folium.Map(
    location = [center_lat, center_lon],
    zoom_start =12
)


merged['bin_category'] = pd.cut(
    merged['total_bins'],
    bins=[0, 1, 3, 6, 11, 16, float('inf')],
    labels=['0 bins', '1-2 bins', '3-5 bins', '6-10 bins', '11-15 bins', '16+ bins']
)

def get_color(bins):
    if bins == 0:
        return 'gray'
    elif bins <= 2:
        return '#C7FFC7' 
    elif bins <= 5:
        return '#69C969' 
    elif bins <= 10:
        return '#2B6B2B'  
    elif bins <=15:
        return '#0D360D'  
    else:
        return '051705'

def style_function(feature):
    bins = feature['properties']['total_bins']
    return {
        'fillColor': get_color(bins),
        'color': 'black',      # outline color
        'weight': 1,           # outline width
        'fillOpacity': 0.9
    }

folium.GeoJson(
    merged,
    style_function=style_function,
    tooltip=folium.GeoJsonTooltip(
        fields=['park_name', 'total_bins'],  # adjust field names as needed
        aliases=['Park:', 'Total Bins:']
    )
).add_to(base_map)

#creating a legend
legend_html = '''
<div style="position: fixed; 
            bottom: 50px; right: 50px; width: 180px; height: auto; 
            background-color: white; z-index:9999; font-size:14px;
            border:2px solid grey; border-radius: 5px; padding: 10px">
<p style="margin-bottom: 5px;"><strong>Bins per Park</strong></p>
<p style="margin: 3px;"><i style="background: gray; width: 20px; height: 20px; 
   display: inline-block; margin-right: 5px;"></i> 0 bins</p>
<p style="margin: 3px;"><i style="background: #C7FFC7; width: 20px; height: 20px; 
   display: inline-block; margin-right: 5px;"></i> 1-2 bins</p>
<p style="margin: 3px;"><i style="background: #69C969; width: 20px; height: 20px; 
   display: inline-block; margin-right: 5px;"></i> 3-5 bins</p>
<p style="margin: 3px;"><i style="background: #2B6B2B; width: 20px; height: 20px; 
   display: inline-block; margin-right: 5px;"></i> 6-10 bins</p>
<p style="margin: 3px;"><i style="background: #0D360D; width: 20px; height: 20px; 
   display: inline-block; margin-right: 5px;"></i> 11-15 bins</p>
<p style="margin: 3px;"><i style="background: #051705; width: 20px; height: 20px; 
   display: inline-block; margin-right: 5px;"></i> 16+ bins</p>
</div>
'''

base_map.get_root().html.add_child(folium.Element(legend_html))




base_map.save('basic-app/outputs/parks_bin_map.html')

