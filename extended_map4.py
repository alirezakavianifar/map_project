import geopandas as gpd
import pandas as pd
import plotly.express as px
import json
import plotly.graph_objects as go
from shapely.geometry import Point
from dash import Dash, dcc, html, Input, Output
import dash  # Import dash module
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
def create_map_figure(selected_region_name=None):
    if selected_region_name:
        # Filter the selected region
        selected_region = economic_regions[economic_regions['ERNAME'] == selected_region_name]
    else:
        # Use all regions if none is selected
        selected_region = economic_regions
    
    # Base map with the selected or all economic regions
    fig = px.choropleth_mapbox(
        selected_region,
        geojson=geojson,
        locations=selected_region.index,
        color="ERNAME",
        center={"lat": 50, "lon": -85},
        mapbox_style="open-street-map",
        zoom=5,
        opacity=0.5,
        labels={'ERNAME': 'Economic Region'}
    )
    
    # If a region is selected, only show branches within that region
    if selected_region_name:
        selected_branches = branches_with_regions[branches_with_regions['ERNAME'] == selected_region_name]
        unique_names = selected_branches['Name'].unique()
        color_map = {name: px.colors.qualitative.Plotly[i % len(px.colors.qualitative.Plotly)] for i, name in enumerate(unique_names)}

        for name in unique_names:
            branch_data = selected_branches[selected_branches['Name'] == name]
            fig.add_trace(go.Scattermapbox(
                lat=branch_data["Lat"],
                lon=branch_data["Long"],
                mode='markers',
                marker=go.scattermapbox.Marker(size=10, color=color_map[name]),
                name=f"{name} in {selected_region_name}",
                text=branch_data["hover"],
                hovertemplate="<b>CU Name:</b> %{text}<extra></extra>"
            ))
    else:
        # Show all branches if no region is selected
        unique_names = cu_branches1['Name'].unique()
        color_map = {name: px.colors.qualitative.Plotly[i % len(px.colors.qualitative.Plotly)] for i, name in enumerate(unique_names)}
        
        for name in unique_names:
            branch_data = cu_branches1[cu_branches1['Name'] == name]
            fig.add_trace(go.Scattermapbox(
                lat=branch_data["Lat"],
                lon=branch_data["Long"],
                mode='markers',
                marker=go.scattermapbox.Marker(size=10, color=color_map[name]),
                name=name,
                text=branch_data["hover"],
                hovertemplate="<b>CU Name:</b> %{text}<extra></extra>"
            ))
    
    # Update layout for better visualization
    fig.update_layout(
        title="<b>Map of Ontario's CU branches by Economic Region</b>",
        margin={"r":0,"t":0,"l":0,"b":0},
        showlegend=True, 
        legend_title_text="CU NAME"
    )
    
    return fig

# Initialize the Dash app
app = Dash(__name__)

app.layout = html.Div([
    dcc.Graph(id='map', figure=create_map_figure(),
              style={"height": "80vh"}),
    html.Button('Reset Map', id='reset-btn', n_clicks=0)  # Add reset button
])

@app.callback(
    Output('map', 'figure'),
    [Input('map', 'clickData'),
     Input('reset-btn', 'n_clicks')]
)
def display_selected_data(clickData, n_clicks):
    ctx = dash.callback_context

    # Identify what triggered the callback
    if ctx.triggered and ctx.triggered[0]['prop_id'] == 'reset-btn.n_clicks':
        # Reset button clicked: Return the original state
        return create_map_figure()

    if clickData:
        # Map click detected: Return the map with selected region highlighted
        location_id = clickData['points'][0]['location']
        selected_region_name = economic_regions.loc[location_id, 'ERNAME']
        return create_map_figure(selected_region_name)
    
    # Default: Return the original state
    return create_map_figure()

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)
