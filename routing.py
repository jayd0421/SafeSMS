import networkx as nx
import osmnx as ox
import streamlit as st
from shapely.geometry import Point
from shapely.ops import linemerge


NETWORK_TYPES = {
    "Drive": "drive",
    "Bike": "bike",
    "Walk": "walk",
    0: "drive",
    1: "bike",
    2: "walk",
}

TRANSPORT_MODES = {
    0: "Drive",
    1: "Bike",
    2: "Walk",
    "Drive": "Drive",
    "Bike": "Bike",
    "Walk": "Walk",
}

MODE_SPEED_KMH = {
    "Drive": 45,
    "Bike": 15,
    "Walk": 5,
}

ALLOWED_HIGHWAYS = {
    "Drive": {
        "motorway",
        "motorway_link",
        "trunk",
        "trunk_link",
        "primary",
        "primary_link",
        "secondary",
        "secondary_link",
        "tertiary",
        "tertiary_link",
        "unclassified",
        "residential",
        "living_street",
        "service",
    },
    "Bike": {
        "cycleway",
        "path",
        "living_street",
        "residential",
        "service",
        "unclassified",
        "tertiary",
        "tertiary_link",
        "secondary",
        "secondary_link",
    },
    "Walk": {
        "footway",
        "pedestrian",
        "steps",
        "path",
        "track",
        "cycleway",
        "living_street",
        "residential",
        "service",
        "unclassified",
        "tertiary",
        "tertiary_link",
    },
}

def get_transport_label(transport_mode):
    return TRANSPORT_MODES.get(transport_mode, "Walk")


def normalize_highway_values(value):
    if isinstance(value, list):
        return {str(item) for item in value}

    if value is None:
        return set()

    return {str(value)}

def highway_allowed(value, transport_mode):
    transport_mode = get_transport_label(transport_mode)
    allowed = ALLOWED_HIGHWAYS[transport_mode]
    return bool(normalize_highway_values(value) & allowed)

def filter_graph_by_highway(graph, transport_mode):
    filtered_graph = graph.copy()
    edges_to_remove = [
        (u, v, key)
        for u, v, key, data in filtered_graph.edges(keys=True, data=True)
        if not highway_allowed(data.get("highway"), transport_mode)
    ]

    filtered_graph.remove_edges_from(edges_to_remove)
    filtered_graph.remove_nodes_from(list(nx.isolates(filtered_graph)))

    return filtered_graph

@st.cache_resource
def get_city_graph(city, transport_mode):
    network_type = NETWORK_TYPES.get(transport_mode, "walk")
    graph = ox.graph.graph_from_place(city, network_type=network_type)
    return filter_graph_by_highway(graph, transport_mode)


def get_selected_grid(grid, grid_ids):
    if not grid_ids:
        return grid.iloc[0:0].copy()

    return grid[grid["grid_id"].isin(grid_ids)].copy()


def find_closest_safety_grid(grid, safety_grid_ids, user_location):
    safety_grid = get_selected_grid(grid, safety_grid_ids)

    if safety_grid.empty:
        return None

    safety_grid_projected = safety_grid.to_crs("EPSG:3857").copy()
    user_point = Point(user_location[1], user_location[0])
    user_point_projected = (
        ox.projection.project_geometry(
            user_point,
            crs="EPSG:4326",
            to_crs="EPSG:3857",
        )[0]
    )

    distances = safety_grid_projected.geometry.centroid.distance(user_point_projected)
    return safety_grid.loc[distances.idxmin()]


def remove_hazard_elements(graph, hazard_grid):
    if hazard_grid.empty:
        return graph.copy()

    safe_graph = graph.copy()
    hazard_projected = hazard_grid.to_crs(graph.graph["crs"])
    nodes, edges = ox.graph_to_gdfs(safe_graph)

    nodes_in_hazard = nodes.sjoin(
        hazard_projected,
        how="inner",
        predicate="intersects",
    )
    edges_in_hazard = edges.sjoin(
        hazard_projected,
        how="inner",
        predicate="intersects",
    )

    safe_graph.remove_nodes_from(nodes_in_hazard.index)
    safe_graph.remove_edges_from(edges_in_hazard.index)
    safe_graph.remove_nodes_from(list(nx.isolates(safe_graph)))

    return safe_graph


def prepare_route_segments(route_gdf):
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
        .agg(
            length=("length", "sum"),
            street_length_m=("street_length_m", "sum"),
            segment_order=("segment_order", "min"),
            geometry=("geometry", merge_geometries),
        )
        .reset_index()
        .sort_values("segment_order")
    )

    return route.__class__(merged, geometry="geometry", crs=route.crs)

def route_to_gdf(graph, origin_location, destination_location):
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
    if isinstance(value, list):
        value = ", ".join(str(item) for item in value if item)

    if value is None or value == "":
        return "Unnamed street"

    return str(value)


def merge_geometries(geometries):
    merged = geometries.unary_union

    try:
        return linemerge(merged)
    except ValueError:
        return merged


def build_routes(city, grid, hazard_grid_ids, safety_grid_ids, user_location, transport_mode):
    closest_safety = find_closest_safety_grid(
        grid,
        safety_grid_ids,
        user_location,
    )

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

    hazard_grid = get_selected_grid(grid, hazard_grid_ids)
    safe_graph = remove_hazard_elements(graph, hazard_grid)

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
    if route_gdf is None or route_gdf.empty or "length" not in route_gdf:
        return None

    return float(route_gdf["length"].sum())


def estimated_time_minutes(route_gdf, transport_mode):
    length_m = route_length(route_gdf)

    if length_m is None:
        return None

    speed_kmh = MODE_SPEED_KMH[get_transport_label(transport_mode)]
    return (length_m / 1000) / speed_kmh * 60


def format_distance(route_gdf):
    length_m = route_length(route_gdf)

    if length_m is None:
        return "N/A"

    if length_m < 1000:
        return f"{length_m:.0f} m"

    return f"{length_m / 1000:.2f} km"


def format_time(route_gdf, transport_mode):
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
