from __future__ import annotations

import folium
import streamlit as st
import random
import math

from branca.element import MacroElement, Template
from streamlit_folium import st_folium

import utils.vector as v

class City:
    def __init__(self, city, grid_size, key):
        """Method to create a city map object

        This method loads the city boundary and grid, stores map bounds, and
        creates the Folium map used by the Streamlit app.

        Parameters
        ----------
        city : str
            The city or place name used to load map layers.
        grid_size : int or float
            The side length used for the hexagonal grid.
        key : str
            The Streamlit-Folium component key for the map.

        Returns
        -------
        None
            This method initializes object attributes.
        """
        self.name = city
        self.key = key

        with st.spinner("Getting city data..."):
            self.boundary, self.grid = v.get_city_grid(city, grid_size)

        self.minx, self.miny, self.maxx, self.maxy = self.boundary.total_bounds

        self.m = folium.Map(
            location=[(self.miny + self.maxy)/2, (self.minx + self.maxx)/2],
            zoom_start=12,
            control_scale=True,
            prefer_canvas=True,
        )

    def get_city_grid(self):
        """Method to get the city grid

        This method returns the grid GeoDataFrame stored on the city map object.

        Returns
        -------
        geopandas.GeoDataFrame
            The hexagonal city grid.
        """
        return self.grid
    
    def add_boundary_to_map(self):
        """Method to add the city boundary to the map

        This method adds the city boundary as a Folium GeoJSON layer and fits
        the map bounds to the city extent.

        Returns
        -------
        None
            This method updates the Folium map object.
        """
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
        """Method to add grid cells to the map

        This method adds the city grid to the Folium map and styles cells as
        hazard, safety, background, or hidden cells.

        Parameters
        ----------
        show_background : bool, optional
            Whether to show non-selected grid cells.
        interactive : bool, optional
            Whether grid cells should expose hover and click interactions.
        hazard_ids : list, optional
            Hazard grid IDs to display.
        safety_ids : list, optional
            Safety grid IDs to display.

        Returns
        -------
        None
            This method updates the Folium map object.
        """
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
            """Function to style one grid feature

            This function delegates grid styling to the vector style helper
            with the current hazard, safety, and background settings.

            Parameters
            ----------
            feature : dict
                The GeoJSON feature being styled.

            Returns
            -------
            dict
                A Folium style dictionary for the feature.
            """
            return v.style_function(
                feature,
                selected_hazard_grids=hazard_ids,
                selected_safety_grids=safety_ids,
                show_background=show_background,
            )

        def highlight(feature):
            """Function to highlight one grid feature

            This function returns the hover style for interactive grid cells.

            Parameters
            ----------
            feature : dict
                The GeoJSON feature being highlighted.

            Returns
            -------
            dict
                A Folium style dictionary for hover highlighting.
            """
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
        """Method to get the clicked grid ID

        This method extracts the grid ID from the last active Folium drawing
        event returned by the Streamlit-Folium component.

        Parameters
        ----------
        map_data : dict
            The data returned by the Streamlit-Folium map component.

        Returns
        -------
        int or None
            The clicked grid ID, or None when no grid was clicked.
        """
        if not map_data:
            return None

        drawing = map_data.get("last_active_drawing")

        if not drawing:
            return None

        properties = drawing.get("properties", {})
        return properties.get("grid_id")

    def add_marker(self, location, tooltip):
        """Method to add a user marker to the map

        This method adds a blue marker to represent the selected user location.

        Parameters
        ----------
        location : list or tuple
            The marker location as ``(latitude, longitude)``.
        tooltip : str
            The tooltip text shown when hovering over the marker.

        Returns
        -------
        None
            This method updates the Folium map object.
        """
        if location is None:
            return

        folium.Marker(
            location=location,
            tooltip=tooltip,
            icon=folium.Icon(color="blue", icon="user"),
        ).add_to(self.m)

    def add_safety_marker(self, location, tooltip):
        """Method to add a safety marker to the map

        This method adds a green marker to represent the closest selected
        safety grid.

        Parameters
        ----------
        location : list or tuple
            The marker location as ``(latitude, longitude)``.
        tooltip : str
            The tooltip text shown when hovering over the marker.

        Returns
        -------
        None
            This method updates the Folium map object.
        """
        if location is None:
            return

        folium.Marker(
            location=location,
            tooltip=tooltip,
            icon=folium.Icon(color="green", icon="ok-sign"),
        ).add_to(self.m)

    def add_route_to_map(self, route_gdf, name, color, opacity=0.8, dash_array=None):
        """Method to add a route to the map

        This method adds a route GeoDataFrame to the Folium map with optional
        street-name tooltips and route styling.

        Parameters
        ----------
        route_gdf : geopandas.GeoDataFrame
            The route segments to display.
        name : str
            The layer name shown for the route.
        color : str
            The route line color.
        opacity : float, optional
            The route line opacity.
        dash_array : str, optional
            The Folium dash pattern for dashed route lines.

        Returns
        -------
        None
            This method updates the Folium map object.
        """
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
        """Method to add a map legend

        This method adds a custom Folium legend for hazard zones, safety zones,
        and route styles when a user location has been selected.

        Parameters
        ----------
        user_location : list or tuple
            The selected user location as ``(latitude, longitude)``.

        Returns
        -------
        None
            This method updates the Folium map object.
        """
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
        """Method to render the Folium map in Streamlit

        This method sends the Folium map to Streamlit and returns selected map
        interaction data from the Streamlit-Folium component.

        Parameters
        ----------
        returned_objects : list, optional
            The Streamlit-Folium interaction objects to return.

        Returns
        -------
        dict
            The map interaction data returned by Streamlit-Folium.
        """
        if returned_objects is None:
            returned_objects = ["last_active_drawing", "last_clicked", "bounds", "zoom"]

        return st_folium(
            self.m, height=560,
            use_container_width=True,
            key=self.key,
            returned_objects=returned_objects,
        )


def toggle_grid(grid_id, grid_type):
    """Function to toggle a selected grid cell

    This function adds or removes a grid ID from the hazard or safety selection
    lists stored in Streamlit session state.

    Parameters
    ----------
    grid_id : int
        The grid ID to toggle.
    grid_type : str
        The target grid type, either ``Hazard`` or ``Safety``.

    Returns
    -------
    None
        This function updates Streamlit session state.
    """
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
    """Function to process a grid click

    This function reads the clicked grid ID from map data and toggles it in the
    selected hazard or safety grid list.

    Parameters
    ----------
    map_data : dict
        The data returned by the Streamlit-Folium map component.
    grid_type : str
        The selected grid type, either ``Hazard`` or ``Safety``.

    Returns
    -------
    None
        This function updates Streamlit session state when a new grid is clicked.
    """
    grid_id = City.get_clicked_grid(map_data)

    if grid_id is None:
        return

    if grid_id == st.session_state.last_selected_grid:
        return

    st.session_state.last_selected_grid = grid_id

    toggle_grid(grid_id, grid_type)

def autogenerate_selected_grids(no_hazard_zones,no_safety_zones,grid,hazard_cluster_size=5,min_boundary_distance=500):
    """Function to autogenerate hazard and safety grids

    This function selects hazard grid cells in clustered groups and safety grid
    cells away from hazards and the city boundary for demo scenarios.

    Parameters
    ----------
    no_hazard_zones : int
        The number of hazard grid cells to generate.
    no_safety_zones : int
        The number of safety grid cells to generate.
    grid : geopandas.GeoDataFrame
        The full city grid GeoDataFrame.
    hazard_cluster_size : int, optional
        The preferred number of hazard cells per cluster.
    min_boundary_distance : int or float, optional
        The minimum distance in metres from the city boundary for generated
        hazard and safety cells.

    Returns
    -------
    None
        This function stores generated grid IDs in Streamlit session state.
    """
    grid = grid.copy()

    total_required = no_hazard_zones + no_safety_zones

    if total_required > len(grid):
        raise ValueError(
            "The number of hazard and safety zones cannot exceed "
            "the number of grids."
        )

    projected = grid.to_crs("EPSG:3857")

    centroids = projected.geometry.centroid

    city_boundary = projected.geometry.union_all().boundary

    # Distance of each grid cell from the city boundary, in metres
    boundary_distance = projected.geometry.distance(city_boundary)

    indices = list(projected.index)

    # Find grids far enough from the boundary
    interior_candidates = [
        i for i in indices
        if boundary_distance.loc[i] >= min_boundary_distance
    ]

    # We require enough interior grids for ALL selected zones.
    if len(interior_candidates) < total_required:
        raise ValueError(
            f"Only {len(interior_candidates)} grids are at least "
            f"{min_boundary_distance} m from the city boundary, but "
            f"{total_required} grids are required."
        )

    # Determine numberof clusters
    no_clusters = math.ceil(no_hazard_zones / hazard_cluster_size)
    no_clusters = min(no_clusters, no_hazard_zones)

    # Choose interior centers
    cluster_centres = []

    # First centre: randomly choose from valid interior grids
    first = random.choice(interior_candidates)
    cluster_centres.append(first)

    while len(cluster_centres) < no_clusters:
        candidates = [
            i for i in interior_candidates
            if i not in cluster_centres
        ]

        if not candidates:
            break

        # Score each candidate based on:
        # 1. Distance from existing cluster centres
        # 2. Distance from boundary
        def centre_score(i):
            """Function to score a candidate hazard cluster centre

            This function scores a grid cell by combining its distance from
            existing hazard cluster centres and its distance from the boundary.

            Parameters
            ----------
            i : int
                The candidate grid index.

            Returns
            -------
            float
                The candidate score used for cluster centre selection.
            """

            distance_from_clusters = min(
                centroids.loc[i].distance(centroids.loc[c])
                for c in cluster_centres
            )
            interior_score = boundary_distance.loc[i]

            return (
                0.9 * distance_from_clusters
                + 0.1 * interior_score
            )

        candidates.sort(key=centre_score, reverse=True)

        # Introduce some randomness while favouring good locations
        pool_size = max(1, min(8, len(candidates)))
        centre = random.choice(candidates[:pool_size])
        cluster_centres.append(centre)

    # Determine size of each cluster
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

    # Only grids sufficiently far from the boundary are available
    available = set(interior_candidates)

    for centre, cluster_size in zip(cluster_centres, cluster_sizes):
        if cluster_size <= 0:
            continue

        candidates = list(available)
        if not candidates:
            break

        # Distance from cluster centre
        distances = {
            i: centroids.loc[i].distance(centroids.loc[centre])
            for i in candidates
        }
        candidates.sort(key=lambda i: distances[i])

        # Take nearby cells, but introduce randomness.
        pool_size = min(len(candidates), max(cluster_size, 8))
        pool = candidates[:pool_size]

        selected = random.sample(pool, min(cluster_size, len(pool)))

        hazard_indices.extend(selected)
        available.difference_update(selected)

    # Safety zone
    safety_indices = []

    # Only grids satisfying the boundary-distance requirement are considered for safety zones.
    candidates = list(available)

    for _ in range(no_safety_zones):
        if not candidates:
            break

        scores = []
        for i in candidates:
            # Distance from nearest hazard
            if hazard_indices:
                distance_from_hazard = min(
                    centroids.loc[i].distance(centroids.loc[h])
                    for h in hazard_indices
                )
            else:
                distance_from_hazard = 0

            # Distance from nearest safety zone
            if safety_indices:
                distance_from_safety = min(
                    centroids.loc[i].distance(centroids.loc[s]) 
                    for s in safety_indices
                )
            else:
                distance_from_safety = 0

            # Distance from city boundary
            interior = boundary_distance.loc[i]

            # Combine score
            score = (
                0.2 * distance_from_hazard
                + 0.60 * distance_from_safety
                + 0.2 * interior
            )

            scores.append((i, score))

        scores.sort(key=lambda x: x[1], reverse=True)

        # Randomly choose from the best candidates
        pool_size = max( 1, min(8, len(scores)))
        chosen = random.choice(scores[:pool_size])[0]

        safety_indices.append(chosen)
        candidates.remove(chosen)

    # Final validation
    selected_indices = (hazard_indices + safety_indices)

    # Make sure no selected grid violates the boundary-distance requirement.
    invalid_indices = [
        i for i in selected_indices
        if boundary_distance.loc[i] < min_boundary_distance
    ]

    if invalid_indices:
        raise ValueError(
            "Some selected grids are too close to the city boundary. Regenerate grid."
            )

    # Save grid IDs
    st.session_state.selected_hazard_grids = (grid.loc[hazard_indices, "grid_id"].tolist())
    st.session_state.selected_safety_grids = (grid.loc[safety_indices, "grid_id"].tolist())
