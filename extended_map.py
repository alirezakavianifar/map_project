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

# Add hover information
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

# Filter for Ontario (assuming PRUID is the correct column for provinces and '35' is Ontario's code)
economic_regions = economic_regions[economic_regions['PRUID'] == '35']

# Prepare GeoJSON for plotting
geojson = json.loads(economic_regions.to_json())

# Create a color map for regions
unique_regions = economic_regions['ERNAME'].unique()
region_color_map = {region: px.colors.qualitative.Plotly[i % len(px.colors.qualitative.Plotly)] for i, region in enumerate(unique_regions)}

# Initialize the map with economic regions
fig = px.choropleth_mapbox(economic_regions,
                           geojson=geojson,
                           locations=economic_regions.index,
                           color="ERNAME",
                           center={"lat": 50, "lon": -85},
                           mapbox_style="open-street-map",
                           zoom=5,
                           opacity=0.5,
                           labels={'ERNAME': 'Economic Region'})

# Update layout for better map visualization
fig.update_layout(
    title="<b>Map of Ontario's CU branches by Economic Region</b>",
    margin={"r":0,"t":0,"l":0,"b":0}
)

# Plot branches within each region
for region_name in unique_regions:
    # Filter branches for the current region
    region_branches = branches_with_regions[branches_with_regions['ERNAME'] == region_name]

    # Add scatter plot for the branches in the current region
    fig.add_trace(go.Scattermapbox(
        lat=region_branches["Lat"],
        lon=region_branches["Long"],
        mode='markers',
        marker=go.scattermapbox.Marker(size=10, color=region_color_map[region_name]),
        name=f"{region_name} CU Branches",
        text=region_branches["hover"],  # Tooltip text
        hovertemplate="<b>CU Branch:</b> %{text}<extra></extra>"
    ))

# Show legend for the scatter plot
fig.update_layout(showlegend=True, legend_title_text="Economic Region & CU Branches")

# Write the output to an HTML file
fig.write_html("Map.html")
