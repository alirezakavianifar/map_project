import geopandas as gpd
import pandas as pd
import plotly.express as px
import json
import plotly.graph_objects as go
from shapely.geometry import Point
from dash import Dash, dcc, html, Input, Output
import dash
import fiona

# Ensure the SHX file is restored if missing or corrupted
with fiona.Env(SHAPE_RESTORE_SHX='YES'):
    economic_regions = gpd.read_file("ler_000a21a_e.shp")

# Load the economic regions shapefile
economic_regions = gpd.read_file("ler_000a21a_e.shp")

# Load the Excel file containing branches
file_path = 'sherkat.xlsx'
cu_branches1 = pd.read_excel(file_path)

# Add a hover text column
cu_branches1['hover'] = cu_branches1.apply(lambda x: f"Branch: {x['Branch']}, CU: {x['Name']}", axis=1)

# Convert branch data to GeoDataFrame
branches = cu_branches1.copy()
branches['geometry'] = branches.apply(lambda x: Point((x['Long'], x['Lat'])), axis=1)
branches_gdf = gpd.GeoDataFrame(branches, geometry='geometry', crs="EPSG:4326")

# Ensure CRS matches
economic_regions = economic_regions.to_crs(epsg=4326)
branches_gdf = branches_gdf.to_crs(economic_regions.crs)

# Spatial join to link branches to regions
branches_with_regions = gpd.sjoin(branches_gdf, economic_regions, how="left", predicate="within")

# Filter for a specific region, e.g., Ontario
economic_regions = economic_regions[economic_regions['PRUID'] == '35']
economic_regions = economic_regions.to_crs(epsg=4326)

# Convert economic regions to GeoJSON for Plotly
geojson = json.loads(economic_regions.to_json())

# Function to create the initial or updated map figure
def create_map_figure(selected_regions=[], selected_company_name=None):
    # Base map figure with all regions
    fig = px.choropleth_mapbox(
        economic_regions,
        geojson=geojson,
        locations=economic_regions.index,
        color="ERNAME",
        center={"lat": 50, "lon": -85},
        mapbox_style="open-street-map",
        zoom=5,
        opacity=0.5,
        labels={'ERNAME': 'Economic Region'}
    )

    # Set all regions as deselected
    fig.update_traces(selector=dict(type='choroplethmapbox'), visible='legendonly')

    # Create a color map for all branch names
    unique_names = cu_branches1['Name'].unique()
    color_map = {name: px.colors.qualitative.Plotly[i % len(px.colors.qualitative.Plotly)] for i, name in enumerate(unique_names)}

    legend_added = set()  # To track which legends have been added

    for name in unique_names:
            branch_data = cu_branches1[cu_branches1['Name'] == name]
            fig.add_trace(go.Scattermapbox(
                lat=branch_data["Lat"],
                lon=branch_data["Long"],
                mode='markers',
                marker=go.scattermapbox.Marker(size=10, color=color_map[name]),
                name=name,
                text=branch_data["hover"],
                hovertemplate="<b>CU Name:</b> %{text}<extra></extra>",
                legendgroup=name,
                showlegend=True,
                visible='legendonly'  # Set initial visibility to 'legendonly' for all branches
            ))
            legend_added.add(name)

    fig.update_layout(
        title="<b>Map of Ontario's CU branches by Economic Region</b>",
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        showlegend=True,
        legend_title_text="CU NAME"
    )

    if len(selected_regions) > 0:
         # Highlight each selected region
        for region in selected_regions:
            region_index = economic_regions[economic_regions['ERNAME'] == region].index
            if not region_index.empty:
                fig.update_traces(selector=dict(locations=[region_index[0]]), visible=True)
            else:
                ...
                # Add traces for non-selected branches with visibility as 'legendonly'
                # non_selected_branch_data = cu_branches1[cu_branches1['Name'] == name]
                # fig.add_trace(go.Scattermapbox(
                #     lat=non_selected_branch_data["Lat"],
                #     lon=non_selected_branch_data["Long"],
                #     mode='markers',
                #     marker=go.scattermapbox.Marker(size=10, color=color_map[name]),
                #     name=name,
                #     text=non_selected_branch_data["hover"],
                #     hovertemplate="<b>CU Name:</b> %{text}<extra></extra>",
                #     legendgroup=name,
                #     showlegend=(name not in legend_added),  # Show legend only if not already added,
                #     visible='legendonly'  # Keep these traces only in the legend
                # ))
                # legend_added.add(name)

        if selected_company_name:
            selected_branches = branches_with_regions[branches_with_regions['Name'] == selected_company_name]
            for name in unique_names:
                branch_data = selected_branches[selected_branches['Name'] == name]
                if not branch_data.empty:
                    fig.add_trace(go.Scattermapbox(
                        lat=branch_data["Lat"],
                        lon=branch_data["Long"],
                        mode='markers',
                        marker=go.scattermapbox.Marker(size=10, color=color_map[name]),
                        name=name,
                        text=branch_data["hover"],
                        hovertemplate="<b>CU Name:</b> %{text}<extra></extra>",
                        legendgroup=name,
                        showlegend=(name not in legend_added),
                        visible=True  # Highlight the legend for branches in the selected region
                    ))
                    legend_added.add(name)

        else:
            selected_branches = branches_with_regions[branches_with_regions['ERNAME'] == region]
            for name in unique_names:
                branch_data = selected_branches[selected_branches['Name'] == name]
                if not branch_data.empty:
                    fig.add_trace(go.Scattermapbox(
                        lat=branch_data["Lat"],
                        lon=branch_data["Long"],
                        mode='markers',
                        marker=go.scattermapbox.Marker(size=10, color=color_map[name]),
                        name=name,
                        text=branch_data["hover"],
                        hovertemplate="<b>CU Name:</b> %{text}<extra></extra>",
                        legendgroup=name,
                        showlegend=(name not in legend_added),
                        visible=True  # Highlight the legend for branches in the selected region
                    ))
                    legend_added.add(name)
    else:
        # No region selected, show all branches in the legend, but not on the map
        ...

    return fig

# Initialize the Dash app
app = Dash(__name__)

app.layout = html.Div([
    dcc.Graph(id='map', figure=create_map_figure(),
              style={"height": "95vh"}),
    html.Button('Reset Map', id='reset-btn', n_clicks=0)
])

@app.callback(
    Output('map', 'figure'),
    [Input('map', 'clickData'),
     Input('reset-btn', 'n_clicks')]
)
def display_selected_data(clickData, n_clicks):
    ctx = dash.callback_context

    if ctx.triggered and ctx.triggered[0]['prop_id'] == 'reset-btn.n_clicks':
        return create_map_figure()

    if clickData:
        selected_regions = []
        point_data = clickData['points'][0]
        if 'location' in point_data:
            location_id = point_data['location']
            selected_regions.append(economic_regions.loc[location_id, 'ERNAME'])
            return create_map_figure(selected_regions)
        else:
            lat, lon = point_data['lat'], point_data['lon']
            selected_branch = branches_with_regions[(branches_with_regions['Lat'] == lat) & 
                                                    (branches_with_regions['Long'] == lon)]
            if not selected_branch.empty:
                selected_region_name = selected_branch.iloc[0]['ERNAME']
                selected_company_name = selected_branch.iloc[0]['Name']
                selected_branches = branches_with_regions[branches_with_regions['Name'] == selected_company_name]
                selected_regions.extend(selected_branches['ERNAME'].unique())
                return create_map_figure(selected_regions, selected_company_name)
    
    return create_map_figure()

if __name__ == '__main__':
    app.run_server(debug=True)
