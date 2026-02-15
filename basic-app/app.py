from shiny import App, ui, reactive, render
from shinywidgets import output_widget, render_widget
import pandas as pd
from ipyleaflet import Map, Marker, MarkerCluster
import plotly.graph_objects as go
from ipywidgets import HTML


# ----------------------------
# Load data
# ----------------------------
df = pd.read_csv(
    "https://raw.githubusercontent.com/h327-uni/shiny_park/main/basic-app/data/parks_cleaned_dups_removed_final.csv"
)

df = df.dropna(subset=["lat", "lon"])
print(df[["lat", "lon"]].head())


park_descriptions = pd.read_csv(
    "https://raw.githubusercontent.com/h327-uni/shiny_park/main/basic-app/data/park_descriptions.csv"
)

park_descriptions["Park Name:"] = (
    park_descriptions["Park Name:"].str.strip()
)

# Create filter columns
df['has_recycling'] = df['key_features'].str.contains('recycling', case=False, na=False)
df['has_dog_waste'] = df['key_features'].str.contains('dog', case=False, na=False)
df['general_waste_only'] = ~df['key_features'].str.contains('recycling', case=False, na=False)


# ----------------------------
# UI
# ----------------------------
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
    

        ui.h5("------------------------"),
        ui.input_checkbox("near_road_only", "Only bins within 100m of roads", value=False),
    ),

    ui.row(
        ui.column(12,
        ui.h1('Auckland Parks Bin Distribution Dashboard',
            style='text-align: center; padding: 20px; background-color: #f0f0f0; margin-bottom: 20px;')
        )
    ),
    
    ui.row(
        ui.column(7, 
            output_widget("map")
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

# ----------------------------
# Server
# ----------------------------


def server(input, output, session):

    m = Map(
    center=(-36.8509, 174.7645),
    zoom=11,
    scroll_wheel_zoom=True
)
    print('Printed map (?)')

    cluster = MarkerCluster()
    m.add_layer(cluster)



    @reactive.calc
    def filtered_data():

        data = df.copy()

        waste_mask = pd.Series(False, index=df.index)

        if input.show_recycling():
            waste_mask = waste_mask | df["has_recycling"]

        if input.show_general_waste():
            waste_mask = waste_mask | df["general_waste_only"]

        if input.show_dog_waste():
            waste_mask = waste_mask | df["has_dog_waste"]

        # If no waste filters selected → show nothing
        if not (
            input.show_recycling() or
            input.show_general_waste() or
            input.show_dog_waste()
        ):
            data = df.iloc[0:0]
        else:
            data = df[waste_mask]

        if input.near_road_only():
            data = data[data["near_road_100m"]]

        print("Filtered rows:", len(data))
        return data


    @render_widget
    def map():
        data = filtered_data()
        park = input.selected_park()

        # Default view
        center = (-36.8509, 174.7645)
        zoom = 11

        # Park zoom (centroid of bins currently visible for that park)
        if park != "All Parks":
            park_data = data[data["park_name"] == park]
            if not park_data.empty:
                center = (float(park_data["lat"].mean()), float(park_data["lon"].mean()))
                zoom = 15
            else:
                # fallback if filters hide all bins in selected park
                park_row = df[df["park_name"] == park].iloc[0]
                center = (float(park_row.lat), float(park_row.lon))
                zoom = 15

        m = Map(center=center, zoom=zoom, scroll_wheel_zoom=True)

        if data.empty:
            return m

        markers = []
        for _, row in data.iterrows():
            recycling_text = "Yes ♻" if row["has_recycling"] else "No"
            general_text = "Yes 🗑" if row["general_waste_only"] else "No"
            dog_text = "Yes 🐶" if row["has_dog_waste"] else "No"
            road_text = "Near road" if row.get("near_road_100m", False) else "Not near road"

            popup_html = HTML(
                value=f"""
                <div style="width: 230px; font-size: 13px;">
                    <strong style="font-size: 15px;">{row['park_name']}</strong>
                    <hr style="margin: 6px 0;">
                    <b>Recycling:</b> {recycling_text}<br>
                    <b>General Waste:</b> {general_text}<br>
                    <b>Dog Waste:</b> {dog_text}<br>
                    <b>Road Proximity:</b> {road_text}<br>
                    <hr style="margin: 6px 0;">
                    <b>Key Features:</b><br>
                    {str(row['key_features']).capitalize()}
                </div>
                """
            )

            markers.append(
                Marker(
                    location=(float(row["lat"]), float(row["lon"])),
                    popup=popup_html
                )
            )

        m.add_layer(MarkerCluster(markers=markers))
        return m


        
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
                near_road_count = int(data["near_road_100m"].sum())
                near_road_percent = (near_road_count / len(data)) * 100 if len(data) > 0 else 0
            else:
                avg_bins = 0
                min_bins = 0
                max_bins = 0
                recycling_bins = 0
                near_road_count = 0
                near_road_percent = 0
            
            return ui.div(
                ui.h4("City Statistics"),
                ui.p(f"Total Bins: {total_bins}"),
                ui.p(f"Parks: {total_parks}"),
                ui.p(f"Avg Bins/Park: {avg_bins:.1f}"),
                ui.p(f"Min Bins/Park: {min_bins}"),
                ui.p(f"Max Bins/Park: {max_bins}"),
                ui.p(f"Bins with Recycling: {recycling_bins}"),
                ui.p(
                    f"Bins within 100m of roads: {near_road_count} "
                    f"({near_road_percent:.1f}%)"
                ),                
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
        
        if selected == "All Parks":
            bins_per_park = data.groupby('park_name').size()
            
            categories = pd.cut(
                bins_per_park,
                bins=[1, 3, 6, 10, 14, float('inf')],
                labels=['1-2 bins', '3-5 bins', '6-9 bins', '10-13 bins', '14+ bins'],
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
            go.Bar(name=f'{selected}', 
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



# ----------------------------
# App
# ----------------------------
app = App(app_ui, server)