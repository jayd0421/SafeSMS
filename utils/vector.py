from __future__ import annotations

import math

import geopandas as gpd
import osmnx as ox
import streamlit as st
from shapely.geometry import Polygon


@st.cache_data(show_spinner=False)
def get_city_boundaries(city: str):
    """Function to get city boundary geometry

    This function geocodes a city or place name with OSMnx and returns the
    matching boundary geometry as a GeoDataFrame.

    Parameters
    ----------
    city : str
        The city or place name to geocode.

    Returns
    -------
    geopandas.GeoDataFrame
        The boundary geometry returned by OSMnx.
    """
    return ox.geocoder.geocode_to_gdf(city)

@st.cache_data(show_spinner=False)
def get_city_road_network(city: str):
    """Function to get city road network edges

    This function downloads an OSM road graph for a city and converts the graph
    edges to a GeoDataFrame for preparation checks and map workflows.

    Parameters
    ----------
    city : str
        The city or place name used to request the road network.

    Returns
    -------
    geopandas.GeoDataFrame
        The road-network edge geometries and OSM attributes.
    """
    graph = ox.graph.graph_from_place(city)
    _, edges = ox.graph_to_gdfs(graph)

    return edges


def reassign_grid_id(grid_gdf: gpd.GeoDataFrame,):
    """Function to assign deterministic grid IDs

    This function sorts grid cells from top-left to bottom-right and assigns
    sequential grid IDs for consistent SMS encoding and decoding.

    Parameters
    ----------
    grid_gdf : geopandas.GeoDataFrame
        The grid cells that should receive deterministic IDs.

    Returns
    -------
    geopandas.GeoDataFrame
        A copy of the input grid with a ``grid_id`` column.
    """

    grid = grid_gdf.copy()

    centroids = grid.geometry.centroid

    grid["_centroid_x"] = centroids.x
    grid["_centroid_y"] = centroids.y

    grid = (grid
        .sort_values(
            by=["_centroid_y","_centroid_x"],
            ascending=[False, True],
        ).reset_index(drop=True)
    )

    grid["grid_id"] = range(1, len(grid) + 1)

    grid = grid.drop(
        columns=[
            "_centroid_x",
            "_centroid_y",
        ]
    )

    return grid

def create_hex_grid(gdf = None, bounds = None, hex_size = 400, overlap = True, crs = "EPSG:3857"):
    """Function to create a regular hexagonal grid

    This function creates hexagonal cells over an input geometry or bounding
    box and optionally keeps only cells that intersect the source geometry.

    Parameters
    ----------
    gdf : geopandas.GeoDataFrame, optional
        The input geometry used to determine the grid extent.
    bounds : tuple, optional
        The bounding box as ``(xmin, ymin, xmax, ymax)`` when no GeoDataFrame is
        provided.
    hex_size : int or float, optional
        The side length of each hexagon in projected CRS units.
    overlap : bool, optional
        Whether to keep only hexagons that intersect the input geometry.
    crs : str, optional
        The projected CRS used while generating the grid.

    Returns
    -------
    geopandas.GeoDataFrame
        The generated hexagonal grid in EPSG:4326 with ``grid_id`` and
        ``area_ha`` columns.
    """

    if gdf is None and bounds is None:
        raise ValueError("Either 'gdf' or 'bounds' must be provided.")

    if overlap and gdf is None:
        raise ValueError("'gdf' must be provided when overlap=True.")

    if gdf is not None:
        source = gdf.to_crs(crs)
        xmin, ymin, xmax, ymax = source.total_bounds

    else:
        source = None
        xmin, ymin, xmax, ymax = bounds


    s = float(hex_size)

    dx = 1.5 * s
    dy = math.sqrt(3) * s

    # Expand bounds slightly so edge cells are not clipped.
    xmin -= 2 * s
    xmax += 2 * s
    ymin -= dy
    ymax += dy

    hexagons = []

    x = xmin
    column = 0

    while x < xmax:
        y_offset = dy/2 if column % 2 else 0
        y = ymin + y_offset

        while y < ymax:
            hexagon = Polygon(
                [
                (x - s, y), 
                (x - s / 2, y + dy / 2),
                (x + s / 2, y + dy / 2),
                (x + s, y),
                (x + s / 2, y - dy / 2),
                (x - s / 2, y - dy / 2),
                ]
            )

            hexagons.append(hexagon)
            y += dy

        x += dx
        column += 1

    grid = gpd.GeoDataFrame(
        {"geometry": hexagons},
        crs=crs,
    )

    if overlap:
        grid = (
            grid
            .sjoin(
                source[["geometry"]],
                how="inner",
                predicate="intersects",
            )
            .drop(
                columns=["index_right"],
                errors="ignore",
            )
            .drop_duplicates(
                subset=["geometry"]
            )
            .reset_index(drop=True)
        )

    grid = reassign_grid_id(grid)

    grid["area_ha"] = (grid.geometry.area / 10_000).round(2)
    return grid.to_crs("EPSG:4326")

@st.cache_data(show_spinner=False)
def get_city_grid(city: str, grid_size: float):
    """Function to get a city boundary and grid

    This function loads a city boundary and creates a hexagonal grid over that
    boundary using the requested grid size.

    Parameters
    ----------
    city : str
        The city or place name used to get the boundary.
    grid_size : int or float
        The side length used for the hexagonal grid.

    Returns
    -------
    tuple
        A tuple containing the boundary GeoDataFrame and the grid GeoDataFrame.
    """
    boundary = get_city_boundaries(city)
    
    grid = create_hex_grid(
        gdf=boundary,
        hex_size=grid_size,
    )
    return boundary, grid

def style_function(feature, selected_hazard_grids=None, selected_safety_grids=None, show_background=True):
    """Function to style a grid feature

    This function returns Folium-compatible style properties for hazard,
    safety, background, and hidden grid cells.

    Parameters
    ----------
    feature : dict
        The GeoJSON feature being styled.
    selected_hazard_grids : list, optional
        Grid IDs that should be styled as hazard zones.
    selected_safety_grids : list, optional
        Grid IDs that should be styled as safety zones.
    show_background : bool, optional
        Whether non-selected grid cells should remain visible.

    Returns
    -------
    dict
        A Folium style dictionary for the grid feature.
    """
    hazard_grids = set(selected_hazard_grids or [])
    safety_grids = set(selected_safety_grids or [])

    grid_id = feature["properties"].get("grid_id")

    if grid_id in hazard_grids:
        return {
            "fillColor": "#e53935",
            "color": "#b71c1c",
            "weight": 1.5,
            "fillOpacity": 0.55,
        }

    if grid_id in safety_grids:
        return {
            "fillColor": "#43a047",
            "color": "#1b5e20",
            "weight": 1.5,
            "fillOpacity": 0.55,
        }

    if not show_background:
        return {
            "fillColor": "transparent",
            "color": "transparent",
            "weight": 0,
            "fillOpacity": 0,
            "opacity": 0,
        }

    return {
        "fillColor": "#ffff00",
        "color": "#636363",
        "weight": 0.5,
        "fillOpacity": 0.10,
    }
