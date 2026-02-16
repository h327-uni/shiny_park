from shinywidgets import render_plotly
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
        ui.input_select(
            "selected_park", "",
            choices=["All Parks"] + sorted(df["park_name"].unique().tolist()),
            selected="All Parks",
        ),

        ui.h5("Filter Bins:"),
        ui.input_checkbox("show_recycling", "Recycling", value=True),
        ui.input_checkbox("show_dog_waste", "Dog Waste Bags", value=True),
        ui.input_checkbox("show_general_waste", "General Waste Only", value=True),

        ui.h5("------------------------"),
        ui.input_checkbox("near_road_only", "Only bins within 100m of roads", value=False),
    ),

    ui.tags.head(
        ui.tags.title("Auckland Parks Bin Distribution Dashboard")
    ),
    
    ui.tags.style("""

    /* Global typography */
:root {
  --ui-font: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", "Liberation Sans", sans-serif;
}

body {
  font-family: var(--ui-font);
  color: #212529;
}

h1, h2, h3, h4, h5 {
  font-weight: 550;
  letter-spacing: -0.2px;
}

    .cardish {
    background: #f8f9fa;
    border-radius: 10px;
    padding: 15px;
    margin-bottom: 10px;
    border: 1px solid rgba(0,0,0,0.06);
    box-shadow: 0 1px 2px rgba(0,0,0,0.04);
    }

    .hist-wrap {
    min-height: 340px;
    }

    .hist-wrap > div {
    width: 100%;
    }


    /* Title card (hero) */
    .title-card {
    background: linear-gradient(180deg, #f8f9fa 0%, #f1f3f5 100%);
    border-radius: 10px;
    padding: 18px 22px;
    margin-bottom: 18px;
    text-align: center;
    border: 1px solid rgba(0,0,0,0.06);
    }

    .app-title {
    margin: 0;
    font-size: 34px;
    font-weight: 650;
    letter-spacing: -0.6px;
    }

    .app-subtitle {
    margin-top: 6px;
    font-size: 16px;
    color: #6c757d;
    }


    .map-wrap .shiny-output-container,
    .map-wrap .shinywidgets-output,
    .map-wrap .widget-subarea,
    .map-wrap .jupyter-widgets,
    .map-wrap .jupyter-widget,
    .map-wrap .widget-container,
    .map-wrap .leaflet,
    .map-wrap .leaflet-container {
    height: 100% !important;
    width: 100% !important;
    min-height: 100% !important;
    }
    """),


    ui.row(
        ui.column(12,
            ui.div(
                ui.h1("Auckland Parks Bin Distribution Dashboard", class_="app-title"),
                ui.div("Interactive overview of bin types and placement patterns across Auckland parks.", class_="app-subtitle"),
                class_="title-card"
            )

        )
    ),

    ui.row(
        ui.column(
            7,
            ui.div(output_widget("map"), class_="map-wrap")  
        ),
        ui.column(
            5,
            ui.div(ui.output_ui("stats_box"), class_="cardish"),
            ui.div(output_widget("histogram_box"), class_="cardish hist-wrap"),
        )
    ),

    ui.row(
        ui.column(
            12,
            ui.div(ui.output_ui("park_description"), class_="cardish")
        )
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

    cluster = MarkerCluster(markers=[])
    m.add_layer(cluster)

    marker_by_idx = {}

    for idx, row in df.iterrows():
        recycling_text = "Yes" if row["has_recycling"] else "No"
        general_text = "Yes" if row["general_waste_only"] else "No"
        dog_text = "Yes" if row["has_dog_waste"] else "No"
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

        marker_by_idx[idx] = Marker(
            location=(float(row["lat"]), float(row["lon"])),
            popup=popup_html
        )

    @reactive.calc
    def filtered_idx():
        waste_mask = pd.Series(False, index=df.index)

        if input.show_recycling():
            waste_mask |= df["has_recycling"]
        if input.show_general_waste():
            waste_mask |= df["general_waste_only"]
        if input.show_dog_waste():
            waste_mask |= df["has_dog_waste"]

        # none selected => show nothing
        if not (input.show_recycling() or input.show_general_waste() or input.show_dog_waste()):
            idx = df.index[:0]
        else:
            idx = df.index[waste_mask]

        if input.near_road_only():
            idx = idx[df.loc[idx, "near_road_100m"]]

        park = input.selected_park()
        if park != "All Parks":
            idx = idx[df.loc[idx, "park_name"] == park]

        return idx


    @reactive.calc
    def filtered_data():
        idx = filtered_idx()
        return df.loc[idx].copy()


    @reactive.effect
    def _update_cluster():
        idx = filtered_idx()
        cluster.markers = [marker_by_idx[i] for i in idx]

    @reactive.effect
    def _center_map():
        park = input.selected_park()

        if park == "All Parks":
            m.center = (-36.8509, 174.7645)
            m.zoom = 11
            return

        park_rows = df[df["park_name"] == park]
        if park_rows.empty:
            return

        m.center = (float(park_rows["lat"].mean()), float(park_rows["lon"].mean()))
        m.zoom = 15

    @render_widget
    def map():
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


    @render_plotly
    def histogram_box():
        data = filtered_data()
        selected = input.selected_park()

        if selected == "All Parks":
            bins_per_park = data.groupby("park_name").size()

            categories = pd.cut(
                bins_per_park,
                bins=[1, 3, 6, 10, 14, float("inf")],
                labels=["1-2 bins", "3-5 bins", "6-9 bins", "10-13 bins", "14+ bins"],
                right=False
            )

            distribution = categories.value_counts().sort_index()

            fig = go.Figure(data=[go.Bar(x=distribution.index.astype(str), y=distribution.values)])
            fig.update_layout(
                paper_bgcolor="#f8f9fa",
                plot_bgcolor="#f8f9fa",
                title=dict(text="Bin Distribution Across Parks", x=0, xanchor='left',
                font=dict(size=16, family="inherit")),
                xaxis_title="Bins per Park",
                yaxis_title="Number of Parks",
                height=300,
                margin=dict(l=40, r=25, t=45, b=40)
            )
            return fig

        # Park-level comparison
        park_data = data[data["park_name"] == selected]
        park_recycling = int(park_data["has_recycling"].sum())
        park_general = int(park_data["general_waste_only"].sum())
        park_dog_waste = int(park_data["has_dog_waste"].sum())

        total_parks = df["park_name"].nunique()
        avg_recycling = df["has_recycling"].sum() / total_parks
        avg_general = df["general_waste_only"].sum() / total_parks
        avg_dog_waste = df["has_dog_waste"].sum() / total_parks

        fig = go.Figure(data=[
            go.Bar(name=f"{selected}", x=["Recycling", "General", "Dog Waste"], y=[park_recycling, park_general, park_dog_waste]),
            go.Bar(name="City Average", x=["Recycling", "General", "Dog Waste"], y=[avg_recycling, avg_general, avg_dog_waste]),
        ])
        fig.update_layout(

            title=dict(text=f"{selected} vs City Average", x=0, xanchor='left',
            font=dict(size=16, family="inherit")),
            yaxis_title="Number of Bins",
            paper_bgcolor="#f8f9fa",
            plot_bgcolor="#f8f9fa",
            barmode="group",
            height=300,
            margin=dict(l=40, r=25, t=45, b=40)
        )
        return fig



# ----------------------------
# App
# ----------------------------
app = App(app_ui, server)