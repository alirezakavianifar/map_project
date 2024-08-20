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

# Add region name to hover information for branch points
branches_with_regions['hover'] = branches_with_regions.apply(
    lambda x: f"Branch: {x['Branch']}, Region: {x['ERNAME']}", axis=1
)

# Convert regions to JSON for Plotly
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

# Add scatter plot for credit union branches with color based on 'Name'
unique_names = cu_branches1['Name'].unique()
color_map = {name: px.colors.qualitative.Plotly[i % len(px.colors.qualitative.Plotly)] for i, name in enumerate(unique_names)}

branch_traces = []
for name in unique_names:
    branch_data = branches_with_regions[branches_with_regions['Name'] == name]
    trace = go.Scattermapbox(
        lat=branch_data["Lat"],
        lon=branch_data["Long"],
        mode='markers',
        marker=go.scattermapbox.Marker(size=10, color=color_map[name]),
        name=name,
        text=branch_data["hover"],  # Tooltip text including branch and region name
        hovertemplate="<b>CU Name:</b> %{text}<extra></extra>",
        visible=True  # Branches should be visible by default
    )
    branch_traces.append(trace)
    fig.add_trace(trace)

# Update layout for better map visualization and legend
fig.update_layout(
    title="<b>Map of Ontario's CU branches by Economic Region</b>",
    margin={"r": 0, "t": 0, "l": 0, "b": 0},
    showlegend=True,
    legend_title_text="Economic Region & CU NAME"
)

# Embed JavaScript for interactivity
custom_js = '''
<script>
document.addEventListener("DOMContentLoaded", function() {
    var plot = document.querySelectorAll("div.plotly-graph-div")[0];

    plot.on('plotly_click', function(data) {
        var point = data.points[0];

        // Extract the region name from the clicked point
        var regionName = point.fullData.name || point.data.name;
        console.log("Extracted region name:", regionName);

        if (!regionName) {
            console.error("Region name could not be determined.");
            return;
        }

        var traces = plot.data.slice(1);  // Skip the first trace which is for regions
        traces.forEach(function(trace) {
            console.log("Processing trace:", trace.name);

            // Ensure we are only processing branch data traces
            if (!trace || trace.geojson || !trace.lat || !trace.text) {
                console.error('Skipping non-branch trace or invalid trace:', trace);
                return;
            }

            var visible = false;
            trace.marker.size = 10;  // Reset the marker size
            trace.marker.opacity = 0.2;  // Reset the marker opacity

            // Iterate through each branch info text
            for (var j = 0; j < trace.text.length; j++) {
                var branchInfo = trace.text[j];
                console.log("Branch info being checked:", branchInfo);

                // Ensure branchInfo is valid and contains expected structure
                if (typeof branchInfo !== 'string') {
                    console.error("Invalid branchInfo:", branchInfo);
                    continue;
                }

                // Enhanced matching logic - case-insensitive and trimmed comparison
                if (branchInfo.toLowerCase().includes(regionName.toLowerCase().trim())) {
                    console.log("Match found for branch:", branchInfo);
                    trace.marker.size = 12;
                    trace.marker.opacity = 1.0;
                    visible = true;
                }
            }
            trace.visible = visible ? true : 'legendonly';
        });
        alert("start");
        Plotly.update(plot, plot.data);
        alert("done");
    });
});
</script>
'''

# Write the map and embed the JavaScript to an HTML file with UTF-8 encoding
with open("Map.html", "w", encoding="utf-8") as f:
    f.write(fig.to_html(full_html=False))
    f.write(custom_js)
    f.write('</body></html>')
