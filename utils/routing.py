import networkx as nx
import osmnx as ox
import streamlit as st
from shapely.geometry import Point
from shapely.ops import linemerge


TRANSPORT_MODES = {
    0: "drive", 1: "bike", 2: "walk",
    "Drive": "drive", "Bike": "bike", "Walk": "walk",
}

MODE_SPEEDS_KMH = {"drive": 45, "bike": 15, "walk": 5}

ALLOWED_HIGHWAYS = {
    "drive": {"motorway", "motorway_link", "trunk", "trunk_link", "primary", "primary_link", "secondary", "secondary_link", "tertiary", "tertiary_link", "unclassified", "residential", "living_street", "service"},
    "bike": {"cycleway", "path", "motorway", "motorway_link", "trunk", "trunk_link", "primary", "primary_link", "secondary", "secondary_link", "tertiary", "tertiary_link", "unclassified", "residential", "living_street", "service"},
    "walk": {"footway", "pedestrian", "steps", "track", "cycleway", "path", "motorway", "motorway_link", "trunk", "trunk_link", "primary", "primary_link", "secondary", "secondary_link", "tertiary", "tertiary_link", "unclassified", "residential", "living_street", "service"},
}

def normalize_highway_values(value):
    """Function to normalize OSM highway values

    This function converts an OSM highway value into a set so single values and
    list values can be checked consistently.

    Parameters
    ----------
    value : str, list, or None
        The raw OSM ``highway`` attribute value.

    Returns
    -------
    set
        A set of highway tag strings.
    """
    if isinstance(value, list):
        return {str(item) for item in value}

    if value is None:
        return set()
    return {str(value)}

def highway_allowed(value, transport_mode):
    """Function to check whether a highway is allowed

    This function checks whether an OSM highway tag is suitable for the
    selected transport mode.

    Parameters
    ----------
    value : str, list, or None
        The raw OSM ``highway`` attribute value.
    transport_mode : int or str
        The selected transport mode key.

    Returns
    -------
    bool
        True when the highway type is allowed for the mode, otherwise False.
    """
    transport_mode = TRANSPORT_MODES[transport_mode]
    allowed = ALLOWED_HIGHWAYS[transport_mode]
    return bool(normalize_highway_values(value) & allowed)

def filter_graph_by_highway(graph, transport_mode):
    """Function to filter a road graph by transport mode

    This function removes road segments whose OSM highway type is not allowed
    for the selected mode of transport.

    Parameters
    ----------
    graph : networkx.MultiDiGraph
        The OSMnx graph to filter.
    transport_mode : int or str
        The selected transport mode key.

    Returns
    -------
    networkx.MultiDiGraph
        A copy of the graph with disallowed edges and isolated nodes removed.
    """
    filtered_graph = graph.copy()
    edges_to_remove = [
        (u, v, key) for u, v, key, data in filtered_graph.edges(keys=True, data=True) 
        if not highway_allowed(data.get("highway"), transport_mode)
    ]

    filtered_graph.remove_edges_from(edges_to_remove)
    filtered_graph.remove_nodes_from(list(nx.isolates(filtered_graph)))
    return filtered_graph

@st.cache_resource
def get_city_graph(city, transport_mode):
    """Function to get a routed city graph

    This function downloads an OSMnx graph for the selected city and transport
    mode, then applies the app's highway-type filter.

    Parameters
    ----------
    city : str
        The city or place name used to request the graph.
    transport_mode : int or str
        The selected transport mode key.

    Returns
    -------
    networkx.MultiDiGraph
        The filtered routing graph.
    """
    network_type = TRANSPORT_MODES[transport_mode]
    graph = ox.graph.graph_from_place(city, network_type=network_type)
    return filter_graph_by_highway(graph, transport_mode)

def get_selected_grids(grid, grid_ids):
    """Function to select grid cells by ID

    This function filters a grid GeoDataFrame to the rows whose ``grid_id``
    values match the requested IDs.

    Parameters
    ----------
    grid : geopandas.GeoDataFrame
        The full grid GeoDataFrame.
    grid_ids : list
        The grid IDs to select.

    Returns
    -------
    geopandas.GeoDataFrame
        A GeoDataFrame containing only the selected grid cells.
    """
    if not grid_ids:
        return grid.iloc[0:0].copy()

    return grid[grid["grid_id"].isin(grid_ids)].copy()

def find_closest_safety_grid(grid, safety_grid_ids, user_location):
    """Function to find the closest safety grid

    This function calculates the nearest selected safety grid to the user's
    location using projected distances.

    Parameters
    ----------
    grid : geopandas.GeoDataFrame
        The full grid GeoDataFrame.
    safety_grid_ids : list
        The selected safety grid IDs.
    user_location : list or tuple
        The user location as ``(latitude, longitude)``.

    Returns
    -------
    pandas.Series or None
        The closest safety grid row, or None when no safety grids are provided.
    """
    safety_grid = get_selected_grids(grid, safety_grid_ids)

    if safety_grid.empty:
        return None

    projected_safety_grid = safety_grid.to_crs("EPSG:3857").copy()
    user_point = Point(user_location[1], user_location[0])
    projected_user_point = (ox.projection.project_geometry(user_point, crs="EPSG:4326", to_crs="EPSG:3857")[0])

    distances = projected_safety_grid.geometry.centroid.distance(projected_user_point)
    return safety_grid.loc[distances.idxmin()]

def remove_hazard_roads(graph, hazard_grid):
    """Function to remove roads intersecting hazard grids

    This function removes graph nodes and edges that intersect selected hazard
    grid cells so recommended routes avoid affected areas where possible.

    Parameters
    ----------
    graph : networkx.MultiDiGraph
        The routing graph to filter.
    hazard_grid : geopandas.GeoDataFrame
        The selected hazard grid cells.

    Returns
    -------
    networkx.MultiDiGraph
        A copy of the graph with hazard-intersecting nodes and edges removed.
    """
    if hazard_grid.empty:
        return graph.copy()

    safe_graph = graph.copy()
    hazard_projected = hazard_grid.to_crs(graph.graph["crs"])
    nodes, edges = ox.graph_to_gdfs(safe_graph)

    nodes_in_hazard = nodes.sjoin(hazard_projected, how="inner", predicate="intersects",)
    edges_in_hazard = edges.sjoin(hazard_projected, how="inner", predicate="intersects")

    safe_graph.remove_nodes_from(nodes_in_hazard.index)
    safe_graph.remove_edges_from(edges_in_hazard.index)
    safe_graph.remove_nodes_from(list(nx.isolates(safe_graph)))
    
    return safe_graph


def prepare_route_segments(route_gdf):
    """Function to prepare route segments for display

    This function adds street-name and length fields to route segments, then
    merges adjacent route pieces by street name for cleaner tooltips and route
    details.

    Parameters
    ----------
    route_gdf : geopandas.GeoDataFrame
        The route segments returned by OSMnx.

    Returns
    -------
    geopandas.GeoDataFrame or None
        The prepared route segments, or the original value when empty or None.
    """
    if route_gdf is None or route_gdf.empty:
        return route_gdf

    route = route_gdf.copy()

    if "name" in route:
        route["street_name"] = route["name"].apply(format_street_name)
    else:
        route["street_name"] = "Unnamed street"

    if "length" not in route:
        route["length"] = route.to_crs("EPSG:3857").length

    route["street_length_m"] = route["length"].round(0).astype(int)
    route["segment_order"] = range(len(route))

    merged = (
        route.groupby("street_name", sort=False)
        .agg(length=("length", "sum"),
            street_length_m=("street_length_m", "sum"),
            segment_order=("segment_order", "min"),
            geometry=("geometry", merge_geometries),
        )
        .reset_index()
        .sort_values("segment_order")
    )

    return route.__class__(merged, geometry="geometry", crs=route.crs)

def route_to_gdf(graph, origin_location, destination_location):
    """Function to calculate a route GeoDataFrame

    This function snaps origin and destination coordinates to graph nodes,
    calculates the shortest path, and converts that path to display segments.

    Parameters
    ----------
    graph : networkx.MultiDiGraph
        The routing graph.
    origin_location : list or tuple
        The origin location as ``(latitude, longitude)``.
    destination_location : list or tuple
        The destination location as ``(latitude, longitude)``.

    Returns
    -------
    geopandas.GeoDataFrame or None
        The route as a GeoDataFrame, or None when no path is found.
    """
    origin_node = ox.distance.nearest_nodes(
        graph,
        origin_location[1],
        origin_location[0],
    )
    destination_node = ox.distance.nearest_nodes(
        graph,
        destination_location[1],
        destination_location[0],
    )

    path = ox.shortest_path(
        graph,
        origin_node,
        destination_node,
        weight="length",
    )

    if path is None:
        return None

    return prepare_route_segments(ox.routing.route_to_gdf(graph, path, weight="length"))


def format_street_name(value):
    """Function to format a street name

    This function converts raw OSM street-name values into a readable string
    for route details and map tooltips.

    Parameters
    ----------
    value : str, list, or None
        The raw OSM street name value.

    Returns
    -------
    str
        A display-ready street name.
    """
    if isinstance(value, list):
        value = ", ".join(str(item) for item in value if item)

    if value is None or value == "":
        return "Unnamed street"

    return str(value)


def merge_geometries(geometries):
    """Function to merge route geometries

    This function merges multiple line geometries into a single geometry where
    possible for route display.

    Parameters
    ----------
    geometries : geopandas.GeoSeries
        The route segment geometries to merge.

    Returns
    -------
    shapely.geometry.base.BaseGeometry
        The merged geometry, or the original union when line merging is not possible.
    """
    merged = geometries.unary_union

    try:
        return linemerge(merged)
    except ValueError:
        return merged


def build_routes(city, grid, hazard_grid_ids, safety_grid_ids, user_location, transport_mode):
    """Function to build shortest and recommended routes

    This function finds the closest safety grid, calculates the shortest route,
    removes roads intersecting hazard grids, and calculates a recommended route.

    Parameters
    ----------
    city : str
        The city or place name used to build the routing graph.
    grid : geopandas.GeoDataFrame
        The full grid GeoDataFrame.
    hazard_grid_ids : list
        The selected hazard grid IDs.
    safety_grid_ids : list
        The selected safety grid IDs.
    user_location : list or tuple
        The user location as ``(latitude, longitude)``.
    transport_mode : int or str
        The selected transport mode key.

    Returns
    -------
    dict
        A dictionary containing the closest safety grid, shortest route,
        recommended route, and any error message.
    """
    closest_safety = find_closest_safety_grid(grid, safety_grid_ids, user_location)

    if closest_safety is None:
        return {
            "closest_safety_grid": None,
            "shortest_route": None,
            "recommended_route": None,
            "error": "No safety grids were provided.",
        }

    destination_point = closest_safety.geometry.representative_point()
    destination_location = (destination_point.y, destination_point.x)
    graph = get_city_graph(city, transport_mode)

    try:
        shortest_route = route_to_gdf(graph, user_location, destination_location)
    except (nx.NetworkXNoPath, nx.NodeNotFound, ValueError):
        shortest_route = None

    hazard_grid = get_selected_grids(grid, hazard_grid_ids)
    safe_graph = remove_hazard_roads(graph, hazard_grid)

    try:
        recommended_route = route_to_gdf(safe_graph, user_location, destination_location)
    except (nx.NetworkXNoPath, nx.NodeNotFound, ValueError):
        recommended_route = None

    return {
        "closest_safety_grid": closest_safety,
        "shortest_route": shortest_route,
        "recommended_route": recommended_route,
        "error": None,
    }


def route_length(route_gdf):
    """Function to calculate route length

    This function sums the segment lengths for a route GeoDataFrame.

    Parameters
    ----------
    route_gdf : geopandas.GeoDataFrame
        The route segments whose lengths should be summed.

    Returns
    -------
    float or None
        The route length in metres, or None when length cannot be calculated.
    """
    if route_gdf is None or route_gdf.empty or "length" not in route_gdf:
        return None

    return float(route_gdf["length"].sum())


def estimated_time_minutes(route_gdf, transport_mode):
    """Function to estimate route travel time

    This function estimates travel time from route length and the configured
    average speed for the selected transport mode.

    Parameters
    ----------
    route_gdf : geopandas.GeoDataFrame
        The route segments to estimate travel time for.
    transport_mode : int or str
        The selected transport mode key.

    Returns
    -------
    float or None
        The estimated travel time in minutes, or None when unavailable.
    """
    length_m = route_length(route_gdf)

    if length_m is None:
        return None

    speed_kmh = MODE_SPEEDS_KMH[TRANSPORT_MODES[transport_mode]]
    return (length_m / 1000) / speed_kmh * 60


def format_distance(route_gdf):
    """Function to format route distance

    This function converts a route length into a human-readable metres or
    kilometres label.

    Parameters
    ----------
    route_gdf : geopandas.GeoDataFrame
        The route segments to format the distance for.

    Returns
    -------
    str
        The formatted route distance.
    """
    length_m = route_length(route_gdf)

    if length_m is None:
        return "N/A"

    if length_m < 1000:
        return f"{length_m:.0f} m"

    return f"{length_m / 1000:.2f} km"


def format_time(route_gdf, transport_mode):
    """Function to format route travel time

    This function converts an estimated route duration into a human-readable
    minutes or hours label.

    Parameters
    ----------
    route_gdf : geopandas.GeoDataFrame
        The route segments to format the travel time for.
    transport_mode : int or str
        The selected transport mode key.

    Returns
    -------
    str
        The formatted route travel time.
    """
    minutes = estimated_time_minutes(route_gdf, transport_mode)

    if minutes is None:
        return "N/A"

    if minutes < 60:
        return f"{minutes:.0f} min"

    hours = int(minutes // 60)
    remainder = int(round(minutes % 60))

    if remainder == 0:
        return f"{hours} hr"

    return f"{hours} hr {remainder} min"
