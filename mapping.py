from __future__ import annotations

import folium
import streamlit as st
import random
import math

from branca.element import MacroElement, Template
from streamlit_folium import st_folium

import vector as v

class City:
    def __init__( self, city, grid_size, key):
        self.name = city
        self.key = key

        with st.spinner("Getting city data..."):
            self.boundary, self.grid = v.get_city_grid(city,grid_size,)

        self.minx, self.miny, self.maxx, self.maxy = self.boundary.total_bounds

        self.m = folium.Map(
            location=[(self.miny + self.maxy)/2, (self.minx + self.maxx)/2],
            zoom_start=12,
            control_scale=True,
            prefer_canvas=True,
        )

    def get_city_grid(self):
        return self.grid
    
    def add_boundary_to_map(self):
        if self.boundary is None or self.boundary.empty:
            return

        folium.GeoJson(
            self.boundary,
            name="Boundary",
            style_function=lambda feature: {
                "color": "blue",
                "weight": 2,
                "fill": False,
            },
            smooth_factor=1,
        ).add_to(self.m)

        self.m.fit_bounds([[self.miny, self.minx], [self.maxy, self.maxx]])

    def add_grid_to_map(self, show_background=True, interactive=True, hazard_ids=None, safety_ids=None):
        if hazard_ids is None:
            hazard_ids = st.session_state.get("selected_hazard_grids", [])

        if safety_ids is None:
            safety_ids = st.session_state.get("selected_safety_grids", [])

        hazard_ids = set(hazard_ids)
        safety_ids = set(safety_ids)

        selected_ids = hazard_ids | safety_ids

        grid = self.grid

        if not show_background:
            grid = grid[grid["grid_id"].isin(selected_ids)]

        if grid.empty:
            return

        def style(feature):
            return v.style_function(
                feature,
                selected_hazard_grids=hazard_ids,
                selected_safety_grids=safety_ids,
                show_background=show_background,
            )

        def highlight(feature):
            if not interactive:
                return {}

            return {"color": "red", "weight": 3, "fillOpacity": 0.6}

        tooltip = None

        if interactive:
            tooltip = folium.GeoJsonTooltip(
                fields=["grid_id", "area_ha"],
                aliases=["Grid ID", "Area (ha)"],
                localize=True, sticky=True,
            )

        folium.GeoJson(
            grid,
            name="Grid",
            style_function=style,
            highlight_function=highlight,
            tooltip=tooltip,
            interactive=interactive,
            zoom_on_click=False,
            smooth_factor=0.5,
            control=False,
        ).add_to(self.m)


    @staticmethod
    def get_clicked_grid(map_data):
        if not map_data:
            return None

        drawing = map_data.get("last_active_drawing")

        if not drawing:
            return None

        properties = drawing.get("properties", {})
        return properties.get("grid_id")

    def add_marker(self, location, tooltip):
        if location is None:
            return

        folium.Marker(
            location=location,
            tooltip=tooltip,
            icon=folium.Icon(color="blue", icon="user"),
        ).add_to(self.m)

    def add_safety_marker(self, location, tooltip):
        if location is None:
            return

        folium.Marker(
            location=location,
            tooltip=tooltip,
            icon=folium.Icon(color="green", icon="ok-sign"),
        ).add_to(self.m)

    def add_route_to_map(self, route_gdf, name, color, opacity=0.8, dash_array=None):
        if route_gdf is None or route_gdf.empty:
            return

        tooltip = None

        if {
            "street_name", "street_length_m",
        }.issubset(route_gdf.columns):

            tooltip = folium.GeoJsonTooltip(
                fields=["street_name", "street_length_m"],
                aliases=["Street", "Length (m)"],
                localize=True, sticky=True,
            )

        folium.GeoJson(
            route_gdf,
            name=name,
            style_function=lambda feature: {
                "color": color, "weight": 5,
                "opacity": opacity,
                "dashArray": dash_array,
            },
            tooltip=tooltip,
            smooth_factor=1,
        ).add_to(self.m)

    def add_legend(self, user_location):
        if user_location is None:
            routes = ""

        else:
            routes = """
            <div>
                <span style="
                    display:inline-block;
                    width:18px;
                    border-top:3px dashed red;
                    opacity:.55;
                    margin-right:6px;
                    vertical-align:middle;
                "></span>
                Shortest route
            </div>
            <div>
                <span style="
                    display:inline-block;
                    width:18px;
                    border-top:3px solid green;
                    margin-right:6px;
                    vertical-align:middle;
                "></span>
                Recommended route
            </div>
            """

        legend = MacroElement()

        legend._template = Template(
            """
            {% macro html(this, kwargs) %}

            <div style="
                position: fixed;
                bottom: 28px;
                left: 28px;
                z-index: 9999;
                background: black;
                color: white;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 10px 12px;
                font-size: 13px;
                box-shadow:
                    0 1px 4px
                    rgba(0, 0, 0, 0.2);
            ">

                <div style="
                    font-weight: 600;
                    margin-bottom: 6px;
                ">
                    Legend
                </div>

                <div>
                    <span style="
                        display:inline-block;
                        width:14px;
                        height:10px;
                        background:red;
                        opacity:.45;
                        margin-right:6px;
                    "></span>
                    Hazard zone
                </div>

                <div>
                    <span style="
                        display:inline-block;
                        width:14px;
                        height:10px;
                        background:green;
                        opacity:.45;
                        margin-right:6px;
                    "></span>
                    Safety zone
                </div>

                """ + routes + """

            </div>

            {% endmacro %}
            """
        )

        self.m.get_root().add_child(legend)

    def add_map(self, returned_objects=None):
        if returned_objects is None:
            returned_objects = ["last_active_drawing", "last_clicked", "bounds", "zoom"]

        return st_folium(
            self.m, height=620,
            use_container_width=True,
            key=self.key,
            returned_objects=returned_objects,
        )


def toggle_grid(grid_id, grid_type):
    hazard_grids = st.session_state.selected_hazard_grids
    safety_grids = st.session_state.selected_safety_grids

    if grid_type == "Hazard":
        if grid_id in safety_grids:
            safety_grids.remove(grid_id)

        if grid_id in hazard_grids:
            hazard_grids.remove(grid_id)

        else:
            hazard_grids.append(grid_id)

    else:
        if grid_id in hazard_grids:
            hazard_grids.remove(grid_id)

        if grid_id in safety_grids:
            safety_grids.remove(grid_id)

        else:
            safety_grids.append(grid_id)


def process_grid_click(map_data, grid_type):
    grid_id = City.get_clicked_grid(map_data)

    if grid_id is None:
        return

    if grid_id == st.session_state.last_selected_grid:
        return

    st.session_state.last_selected_grid = grid_id

    toggle_grid(grid_id, grid_type)


def autogenerate_selected_grids(no_hazard_zones, no_safety_zones, grid, hazard_cluster_size=5):
    grid = grid.copy()

    total_required = no_hazard_zones + no_safety_zones

    if total_required > len(grid):
        raise ValueError("The number of hazard and safety zones cannot exceed the number of grids.")

    projected = grid.to_crs("EPSG:3857")
    centroids = projected.geometry.centroid

    city_boundary = projected.geometry.union_all().boundary

    boundary_distance = projected.geometry.distance(city_boundary)

    indices = list(projected.index)

    no_clusters = math.ceil(no_hazard_zones / hazard_cluster_size)
    no_clusters = min(no_clusters, no_hazard_zones)

    # Find suitable interior cells for cluster centres
    # Only consider cells that are reasonably far from the boundary.
    interior_threshold = boundary_distance.quantile(0.40)

    interior_candidates = [i for i in indices if boundary_distance.loc[i] >= interior_threshold]

    # Option in case the grid is very small.
    if len(interior_candidates) < no_clusters:
        interior_candidates = indices.copy()

    # Choose separated interior cluster centres
    cluster_centres = []

    # First centre: randomly choose from the interior.
    first = random.choice(
        interior_candidates
    )

    cluster_centres.append(first)

    while len(cluster_centres) < no_clusters:

        candidates = [
            i for i in interior_candidates
            if i not in cluster_centres
        ]

        if not candidates:
            break

        # Score each candidate according to:
        # 1. Distance from existing clusters
        # 2. Distance from boundary
        def centre_score(i):
            distance_from_clusters = min(
                centroids.loc[i].distance(centroids.loc[c])
                for c in cluster_centres
            )

            interior_score = (boundary_distance.loc[i])

            return 0.5 * distance_from_clusters + 0.5 * interior_score

        candidates.sort(key=centre_score,reverse=True)
        
        # Some randomness while still favouring good interior locations.
        pool_size = max(1, min(8, len(candidates)),)

        centre = random.choice( candidates[:pool_size])
        cluster_centres.append(centre)

    base_size = no_hazard_zones // no_clusters

    remainder = no_hazard_zones % no_clusters

    cluster_sizes = []

    for i in range(no_clusters):
        size = base_size

        if i < remainder:
            size += 1

        cluster_sizes.append(size)

    # Grow hazard clusters
    hazard_indices = []
    available = set(indices)

    for centre, cluster_size in zip(cluster_centres, cluster_sizes):

        if cluster_size <= 0:
            continue

        candidates = list(available)

        # Distance from cluster centre.
        distances = {
            i: centroids.loc[i].distance(
                centroids.loc[centre]
            )
            for i in candidates
        }

        candidates.sort(key=lambda i: distances[i])

        # Take nearby cells, but introduce randomness.
        # For 5 cells, consider roughly the nearest 10 cells and randomly choose 5.
        pool_size = min(
            len(candidates),
            max(cluster_size, 8),
        )

        pool = candidates[:pool_size]

        selected = random.sample(pool, min(cluster_size,len(pool)))

        hazard_indices.extend(selected)
        available.difference_update(selected)

    # SAFETY ZONES
    safety_indices = []
    candidates = list(available)

    for _ in range( no_safety_zones):
        if not candidates:
            break

        scores = []

        for i in candidates:
            # Distance from nearest hazard.
            distance_from_hazard = min(
                centroids.loc[i].distance(centroids.loc[h])
                for h in hazard_indices
            )

            # Distance from nearest safety zone.
            if safety_indices:
                distance_from_safety = min(
                    centroids.loc[i].distance(centroids.loc[s])
                    for s in safety_indices
                )

            else:
                distance_from_safety = 0

            # Distance from city boundary.
            interior = (boundary_distance.loc[i])

            score = (
                0.2 * distance_from_hazard
                + 0.60 * distance_from_safety
                + 0.2 * interior
            )

            scores.append((i, score))

        scores.sort(key=lambda x: x[1], reverse=True)

        # Randomly choose from the best candidates.
        pool_size = max(1, min(8, len(scores)))

        chosen = random.choice(scores[:pool_size])[0]

        safety_indices.append(chosen)
        candidates.remove(chosen)

    # Save grid IDs
    st.session_state.selected_hazard_grids = (grid.loc[hazard_indices, "grid_id"].tolist())
    st.session_state.selected_safety_grids = (grid.loc[safety_indices, "grid_id"].tolist())
