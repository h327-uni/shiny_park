from shiny import App, ui, reactive, render
import pandas as pd
import folium
from folium.plugins import MarkerCluster
import plotly.graph_objects as go
from shinywidgets import render_widget

# Load your data
df = pd.read_csv('basic-app\data\parks_cleaned_dups_removed_final.csv')
park_descriptions = pd.read_csv('basic-app\data\park_descriptions.csv')

park_descriptions["Park Name:"] = (
    park_descriptions["Park Name:"].str.strip()
)


# Create filter columns
df['has_recycling'] = df['key_features'].str.contains('recycling', case=False, na=False)
df['has_dog_waste'] = df['key_features'].str.contains('dog', case=False, na=False)
df['general_waste_only'] = ~df['key_features'].str.contains('recycling', case=False, na=False)

# UI
app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.p("Explore bin distribution across Auckland parks using VGI data."),

        ui.h5("Select Park:"),
            ui.input_select("selected_park", "", 
                choices=["All Parks"] + sorted(df['park_name'].unique().tolist())),
   
        
        ui.h5("Filter Bins:"),
        ui.input_checkbox("show_recycling", "Recycling", value=True),
        ui.input_checkbox("show_dog_waste", "Dog Waste Bags", value=True),
        ui.input_checkbox("show_general_waste", "General Waste Only", value=True),
    ),

    ui.row(
        ui.column(12,
        ui.h1('Auckland Parks Bin Distribution Dashboard',
            style='text-align: center; padding: 20px; background-color: #f0f0f0; margin-bottom: 20px;')
        )
    ),
    
    ui.row(
        ui.column(7, 
            ui.output_ui("bin_map")
        ),
        ui.column(5,
            ui.output_ui("stats_box"),
            ui.output_ui("histogram_box")
        )
    ),
    ui.row(
        ui.column(12, ui.output_ui("park_description"))
    )
)

def server(input, output, session):
    
    @reactive.calc
    def filtered_data():
        data = pd.DataFrame()
        
        if input.show_recycling():
            recycling_bins = df[df['has_recycling']]
            data = pd.concat([data, recycling_bins])

        if input.show_general_waste(): 
            general_bins = df[df['general_waste_only']]
            data = pd.concat([data, general_bins])
        
        if input.show_dog_waste():
            dog_bins = df[df['has_dog_waste']]
            data = pd.concat([data, dog_bins])
        
        data = data.drop_duplicates()
        return data
        
    @render.ui
    def stats_box():
        data = filtered_data()
        selected = input.selected_park()

        if selected == 'All Parks':
            total_bins = len(data)
            total_parks = data['park_name'].nunique()
        
            if total_bins > 0 and total_parks > 0:
                bins_per_park = data.groupby('park_name').size()
                
                avg_bins = total_bins / total_parks
                min_bins = bins_per_park.min()
                max_bins = bins_per_park.max()
                recycling_bins = int(data['has_recycling'].sum())
            else:
                avg_bins = 0
                min_bins = 0
                max_bins = 0
                recycling_bins = 0
            
            return ui.div(
                ui.h4("City Statistics"),
                ui.p(f"Total Bins: {total_bins}"),
                ui.p(f"Parks: {total_parks}"),
                ui.p(f"Avg Bins/Park: {avg_bins:.1f}"),
                ui.p(f"Min Bins/Park: {min_bins}"),
                ui.p(f"Max Bins/Park: {max_bins}"),
                ui.p(f"Bins with Recycling: {recycling_bins}"),
                style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 10px;"
            )
        else:
            park_data = data[data['park_name'] == selected]
            total_bins = len(park_data)
            recycling_bins = int(park_data['has_recycling'].sum())
            dog_bins = int(park_data['has_dog_waste'].sum())

            return ui.div(
                ui.h4(f"{selected}"),
                ui.p(f"Total bins: {total_bins}"),
                ui.p(f"Recycling bins: {recycling_bins}"),
                ui.p(f"Bins with dog waste bags: {dog_bins}"),
                style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 10px;"
            )
        
    @render.ui
    def bin_map():
        data = filtered_data()
        selected = input.selected_park()
        
        # Determine map center and zoom based on selection
        if selected == "All Parks":
            center_lat = -36.8485
            center_lon = 174.7633
            zoom = 12
        else:
            # Calculate centroid of selected park's bins
            park_data = data[data['park_name'] == selected]
            if len(park_data) > 0:
                center_lat = park_data['lat'].mean()
                center_lon = park_data['lon'].mean()
                zoom = 16  # Closer zoom for individual park
            else:
                # Fallback if park has no bins matching filters
                center_lat = -36.8485
                center_lon = 174.7633
                zoom = 12
        
        m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom)
        marker_cluster = MarkerCluster().add_to(m)
        
        for idx, row in data.iterrows():
            recycling_text = "Yes" if row['has_recycling'] else "No"
            
            popup_html = f"""
            <div style="font-family: Arial; font-size: 12px;">
                <b>Park:</b> {row['park_name']}<br>
                <b>Features:</b> {str(row['key_features']).capitalize()}<br>
                <b>Recycling:</b> {recycling_text}
            </div>
            """

            folium.Marker(
                location=[row['lat'], row['lon']],
                popup=folium.Popup(popup_html, max_width=300),
                icon=folium.Icon(color='green', icon="trash")
            ).add_to(marker_cluster)
        
        return ui.HTML(m._repr_html_())
    

    @render.ui
    def park_description():
        selected = input.selected_park()

        # Default message
        fallback = ui.div(
            "Further park details coming soon...",
            style="padding: 15px; background-color: #f8f9fa; margin-top: 10px;"
        )

        if selected == "All Parks":
            return 'Select a park from the dropdown to view further details. Parks with descriptions currently loaded: Auckland Domain, Maungakiekie/One Tree Hill, Maungawhau/Mount Eden and Onepoto Domain.'

        match = park_descriptions[
            park_descriptions["Park Name:"] == selected
        ]

        if match.empty:
            return fallback

        row = match.iloc[0]

        park_name = row["Park Name:"]
        size = row["Size"]
        description = row["Description"]
        source = row["Source"]

        # Split description into paragraphs
        paragraphs = [
            ui.p(p.strip())
            for p in description.split("\n\n")
            if p.strip()
        ]

        # Source footer (linked if URL)
        source_ui = (
            ui.a(source, href=source, target="_blank")
            if source.startswith("http")
            else source
        )

        return ui.div(
            # Header row
            ui.div(
                ui.strong(park_name),
                ui.span(f"Size: {size:.1f} ha", style="float: right;"),
                style="font-size: 1.1em; margin-bottom: 10px;"
            ),

            # Description paragraphs
            *paragraphs,

            ui.hr(),

            # Source footer
            ui.div(
                ui.span("Adapted from "),
                source_ui,
                style="font-size: 0.85em; color: #6c757d;"
            ),

            style="padding: 15px; background-color: #f8f9fa; margin-top: 10px;"
        )


    
    @render.ui
    def histogram_box():
        data = filtered_data()
        selected = input.selected_park()
        print(selected)
        
        if selected == "All Parks":
            bins_per_park = data.groupby('park_name').size()
            
            categories = pd.cut(
                bins_per_park,
                bins=[1, 3, 6, 9, 11, float('inf')],
                labels=['1-2 bins', '3-5 bins', '6-8 bins', '9-10 bins', '11+ bins'],
                right=False
            )
            
            distribution = categories.value_counts().sort_index()
            
            fig = go.Figure(data=[
                go.Bar(
                    x=distribution.index.astype(str),
                    y=distribution.values,
                    marker_color='steelblue'
                )
            ])
            
            fig.update_layout(
                title="Bin Distribution Across Parks",
                xaxis_title="Bins per Park",
                yaxis_title="Number of Parks",
                height=300,
                margin=dict(l=40, r=40, t=40, b=40)
            )
            
            return ui.HTML(fig.to_html(include_plotlyjs="cdn", full_html=False))
        
        # Park-level comparison (if not "All Parks")
        park_data = data[data['park_name'] == selected]
        
        park_recycling = int(park_data['has_recycling'].sum())
        park_general = int(park_data['general_waste_only'].sum())
        park_dog_waste = int(park_data['has_dog_waste'].sum())
        
        total_parks = df['park_name'].nunique()
        avg_recycling = df['has_recycling'].sum() / total_parks
        avg_general = df['general_waste_only'].sum() / total_parks
        avg_dog_waste = df['has_dog_waste'].sum() / total_parks
        
        fig = go.Figure(data=[
            go.Bar(name='This Park', 
                x=['Recycling', 'General', 'Dog Waste'], 
                y=[park_recycling, park_general, park_dog_waste],
                marker_color='steelblue'),
            go.Bar(name='City Average', 
                x=['Recycling', 'General', 'Dog Waste'], 
                y=[avg_recycling, avg_general, avg_dog_waste],
                marker_color='lightgray')
        ])
        
        fig.update_layout(
            title=f"{selected} vs City Average",
            yaxis_title="Number of Bins",
            barmode='group',
            height=300,
            margin=dict(l=40, r=40, t=40, b=40)
        )
        
        return ui.HTML(fig.to_html(include_plotlyjs="cdn", full_html=False))

app = App(app_ui, server)