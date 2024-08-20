import geopandas as gpd
import pandas as pd
import plotly.express as px
import json
import plotly.graph_objects as go
from shapely.geometry import Point
from dash import Dash, dcc, html, Input, Output
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
cu_branches1['hover'] = cu_branches1.apply(lambda x: f"Branch: {x['Branch']}", axis=1)

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

# Function to create the initial map figure
def create_map_figure(selected_region_name=None):
    # Base map with economic regions
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
    
    # Add scatter plot for credit union branches
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
    
    # Highlight branches within the selected region, if applicable
    if selected_region_name:
        selected_branches = branches_with_regions[branches_with_regions['ERNAME'] == selected_region_name]
        fig.add_trace(go.Scattermapbox(
            lat=selected_branches["Lat"],
            lon=selected_branches["Long"],
            mode='markers',
            marker=dict(size=15, color='red', symbol='star'),
            name=f"Selected: {selected_region_name}",
            text=selected_branches["hover"],
            hovertemplate="<b>Selected CU:</b> %{text}<extra></extra>"
        ))
    
    # Update layout for better visualization
    fig.update_layout(
        title="<b>Map of Ontario's CU branches by Economic Region</b>",
        margin={"r":0,"t":0,"l":0,"b":0},
        showlegend=True, 
        legend_title_text="Economic Region & CU NAME"
    )
    
    return fig

# Initialize the Dash app
app = Dash(__name__)

app.layout = html.Div([
    dcc.Graph(id='map', figure=create_map_figure()),
])

@app.callback(
    Output('map', 'figure'),
    Input('map', 'clickData')
)
def display_selected_data(clickData):
    if clickData is None:
        return create_map_figure()
    
    # Extract the location ID from the click data
    location_id = clickData['points'][0]['location']
    selected_region_name = economic_regions.loc[location_id, 'ERNAME']
    
    # Create a new figure with the selected region highlighted
    return create_map_figure(selected_region_name)

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)
