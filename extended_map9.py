import geopandas as gpd
import fiona
import pandas as pd
import plotly.express as px
import json
import plotly.graph_objects as go
from shapely.geometry import Point

# Ensure the SHX file is restored if missing or corrupted
with fiona.Env(SHAPE_RESTORE_SHX='YES'):
    economic_regions = gpd.read_file("ler_000a21a_e.shp")

# Load the economic regions shapefile
economic_regions = gpd.read_file("ler_000a21a_e.shp")
file_path = 'sherkat.xlsx'
cu_branches1 = pd.read_excel(file_path)

cu_branches1['hover'] = cu_branches1.apply(lambda x: f"Branch: {x['Branch']}", axis=1)

# Step 1: Convert branch data to GeoDataFrame
branches = cu_branches1.copy()
branches['geometry'] = branches.apply(lambda x: Point((x['Long'], x['Lat'])), axis=1)
branches_gdf = gpd.GeoDataFrame(branches, geometry='geometry', crs="EPSG:4326")

# Step 2: Ensure CRS matches
economic_regions = economic_regions.to_crs(epsg=4326)
branches_gdf = branches_gdf.to_crs(economic_regions.crs)

# Step 3: Spatial join to link branches to regions
branches_with_regions = gpd.sjoin(branches_gdf, economic_regions, how="left", predicate="within")

# Filter for Ontario (assuming PRUID is the correct column for provinces and '35' is Ontario's code)
economic_regions = economic_regions[economic_regions['PRUID'] == '35']

economic_regions = economic_regions.to_crs(epsg=4326)
geojson = json.loads(economic_regions.to_json())

# Create choropleth mapbox figure for economic regions
fig = px.choropleth_mapbox(economic_regions,
                           geojson=geojson,
                           locations=economic_regions.index,
                           color="ERNAME",
                           center={"lat": 50, "lon": -85},
                           mapbox_style="open-street-map",
                           zoom=5,
                           opacity=0.5,
                           labels={'ERNAME': 'Economic Region'})

# Set all regions as deselected
fig.update_traces(selector=dict(type='choroplethmapbox'), visible='legendonly')

# Add scatter plot for credit union branches with color based on 'Name'
unique_names = cu_branches1['Name'].unique()
color_map = {name: px.colors.qualitative.Plotly[i % len(px.colors.qualitative.Plotly)] for i, name in enumerate(unique_names)}

# Adding branches to the map
for name in unique_names:
    branch_data = cu_branches1[cu_branches1['Name'] == name]
    fig.add_trace(go.Scattermapbox(
        lat=branch_data["Lat"],
        lon=branch_data["Long"],
        mode='markers',
        marker=go.scattermapbox.Marker(size=10, color=color_map[name]),
        name=name,
        text=branch_data["hover"],  # Tooltip text
        hovertemplate="<b>CU Name:</b> %{text}<extra></extra>",
        visible='legendonly'  # Set branches as deselected
    ))

# Adding region-specific traces for branch highlighting
for region_name in economic_regions['ERNAME'].unique():
    region_branches = branches_with_regions[branches_with_regions['ERNAME'] == region_name]
    fig.add_trace(go.Scattermapbox(
        lat=region_branches["Lat"],
        lon=region_branches["Long"],
        mode='markers',
        marker=go.scattermapbox.Marker(size=10, color='red'),  # Highlight color for branches
        name=f"Region-specific {region_name} Branches",  # Region-specific indicator before the region name
        visible='legendonly',  # Initially hidden
    ))

# Update layout for better map visualization and legend
fig.update_layout(
    title="<b>Map of Ontario's CU branches by Economic Region</b>",
    margin={"r": 0, "t": 0, "l": 0, "b": 0},
    showlegend=True,
    legend_title_text="Economic Region & CU NAME"
)

# Write the map to an HTML file
fig.write_html("Map.html")
