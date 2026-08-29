import streamlit as st

import math
import numpy as np

import osmnx as ox
import geopandas as gpd
import shapely
from shapely.geometry import Polygon
from shapely.geometry import box

def get_city_boundaries(city="Salzburg, Austria"):
    city_admin_boundaries = ox.geocoder.geocode_to_gdf(city)
    return city_admin_boundaries

def get_city_road_network(city="Salzburg, Austria"):
    graph = ox.graph.graph_from_place(city)
    _, edges = ox.graph_to_gdfs(graph)
    return edges

def reassign_grid_id(grid_gdf):
    # grid_gdf = your grid GeoDataFrame

    # Use centroid coordinates for sorting
    grid_gdf["centroid_x"] = grid_gdf.geometry.centroid.x
    grid_gdf["centroid_y"] = grid_gdf.geometry.centroid.y

    # Sort from top-left:
    # y descending = top to bottom
    # x ascending = left to right
    grid_gdf = grid_gdf.sort_values(
        by=["centroid_y", "centroid_x"],
        ascending=[False, True]
    ).reset_index(drop=True)

    # Assign grid IDs
    grid_gdf["grid_id"] = range(1, len(grid_gdf) + 1)

    # Optional to remove helper columns
    grid_gdf = grid_gdf.drop(columns=["centroid_x", "centroid_y"])
    return grid_gdf

# def create_grid(gdf=None, bounds=None, n_cells=10, overlap=False, crs="EPSG:3857"):
#     """Create square grid that covers a geodataframe area
#     or a fixed boundary with x-y coords
#     returns: a GeoDataFrame of grid polygons
#     see https://james-brennan.github.io/posts/fast_gridding_geopandas/
#     """
    
#     gdf = gdf.to_crs(epsg=crs[-4:])
    
#     if bounds is not None:
#         xmin, ymin, xmax, ymax= bounds
#     else:
#         xmin, ymin, xmax, ymax= gdf.total_bounds

#     # get cell size
#     cell_size = (xmax-xmin)/n_cells
#     # create the cells in a loop
#     grid_cells = []
#     for x0 in np.arange(xmin, xmax+cell_size, cell_size):
#         for y0 in np.arange(ymin, ymax+cell_size, cell_size):
#             x1 = x0-cell_size
#             y1 = y0+cell_size
#             poly = shapely.geometry.box(x0, y0, x1, y1)
#             #print (gdf.overlay(poly, how='intersection'))
#             grid_cells.append(poly)

#     cells = gpd.GeoDataFrame(grid_cells, columns=['geometry'],
#                                      crs=crs)
#     # cells["grid_area"] = round(cells.area/10000,1)
    
#     if overlap == True:
#         # cols = ['grid_id','geometry','grid_area']
#         cells = cells.sjoin(gdf, how='inner').drop_duplicates('geometry')
#         cells = cells[[cells.geometry.name]]
#         cells = cells.reset_index().rename(columns={"index": "grid_id"})
#         cells["grid_area_ha"] = round(cells.area/10_000,1)
        
#     cells = cells.to_crs(epsg="4326")
#     return cells

# def create_hex_grid(gdf=None, bounds=None, n_cells=10, overlap=False, crs="EPSG:3857"):
#     """Hexagonal grid over geometry.
#     See https://sabrinadchan.github.io/data-blog/building-a-hexagonal-cartogram.html
#     """
#     gdf = gdf.to_crs(epsg=crs[-4:])
    
#     if bounds is not None:
#         xmin, ymin, xmax, ymax= bounds
#     else:
#         xmin, ymin, xmax, ymax= gdf.total_bounds

#     unit = (xmax-xmin)/n_cells
#     a = np.sin(np.pi / 3)
#     cols = np.arange(np.floor(xmin), np.ceil(xmax), 3 * unit)
#     rows = np.arange(np.floor(ymin) / a, np.ceil(ymax) / a, unit)

#     #print (len(cols))
#     hexagons = []
#     for x in cols:
#       for i, y in enumerate(rows):
#         if (i % 2 == 0):
#           x0 = x
#         else:
#           x0 = x + 1.5 * unit

#         hexagons.append(Polygon([
#           (x0, y * a),
#           (x0 + unit, y * a),
#           (x0 + (1.5 * unit), (y + unit) * a),
#           (x0 + unit, (y + (2 * unit)) * a),
#           (x0, (y + (2 * unit)) * a),
#           (x0 - (0.5 * unit), (y + unit) * a),
#         ]))

#     grid = gpd.GeoDataFrame({'geometry': hexagons},crs=crs)
#     if overlap == True:
#         cols = ['grid_id','geometry','grid_area']
#         grid = grid.sjoin(gdf, how='inner').drop_duplicates('geometry')
        
#         grid = grid[[grid.geometry.name]]
#         grid = reassign_grid_id(grid)
#         # grid = grid.reset_index().rename(columns={"index": "grid_id"})
#         grid["grid_area_ha"] = round(grid.area/10_000,1)
        
#     grid = grid.to_crs(epsg="4326")
#     return grid

def create_grid(
    gdf=None,
    bounds=None,
    cell_size=1000,
    overlap=False,
    crs="EPSG:3857",
):
    """
    Create a square grid with a specified physical cell size.

    Parameters
    ----------
    gdf : GeoDataFrame, optional
        Input geometries used to determine the extent.
    bounds : tuple, optional
        (xmin, ymin, xmax, ymax). Used if gdf is None.
    cell_size : float
        Grid cell size in CRS units (e.g. metres).
    overlap : bool
        If True, only keep cells intersecting the input geometry.
    crs : str
        Projected CRS used to build the grid.

    Returns
    -------
    GeoDataFrame
        Grid polygons with attributes:
            - grid_id
            - area_ha
            - geometry
    """

    if gdf is None and bounds is None:
        raise ValueError("Either 'gdf' or 'bounds' must be provided.")

    if gdf is not None:
        gdf = gdf.to_crs(crs)
        xmin, ymin, xmax, ymax = gdf.total_bounds
    else:
        xmin, ymin, xmax, ymax = bounds

    n_cols = math.ceil((xmax - xmin) / cell_size)
    n_rows = math.ceil((ymax - ymin) / cell_size)

    grid_cells = []

    for col in range(n_cols):
        for row in range(n_rows):
            x0 = xmin + col * cell_size
            y0 = ymin + row * cell_size

            grid_cells.append(
                box(
                    x0,
                    y0,
                    x0 + cell_size,
                    y0 + cell_size,
                )
            )

    grid = gpd.GeoDataFrame(
        geometry=grid_cells,
        crs=crs,
    )

    if overlap:
        if gdf is None:
            raise ValueError("'gdf' must be provided when overlap=True.")

        grid = (
            grid.sjoin(
                gdf,
                how="inner",
                predicate="intersects",
            )
            .drop_duplicates(subset="geometry")
            [[grid.geometry.name]]
            .reset_index(drop=True)
        )

    grid = grid.reset_index(drop=True)
    grid["grid_id"] = grid.index
    grid["area_ha"] = (grid.area / 10_000).round(2)

    return grid.to_crs("EPSG:4326")

def create_hex_grid(
    gdf=None,
    bounds=None,
    hex_size=500,
    overlap=False,
    crs="EPSG:3857",
):
    """
    Create a regular hexagonal grid.

    Parameters
    ----------
    gdf : GeoDataFrame, optional
        Input geometries used to determine the extent.
    bounds : tuple, optional
        (xmin, ymin, xmax, ymax). Used if gdf is None.
    hex_size : float
        Side length of each hexagon in CRS units (e.g. metres).
    overlap : bool
        If True, only keep hexagons intersecting the input geometry.
    crs : str
        Projected CRS used for grid generation.

    Returns
    -------
    GeoDataFrame
        Hexagonal grid with:
            - grid_id
            - area_ha
            - geometry
    """

    if gdf is None and bounds is None:
        raise ValueError("Either 'gdf' or 'bounds' must be provided.")

    if gdf is not None:
        gdf = gdf.to_crs(crs)
        xmin, ymin, xmax, ymax = gdf.total_bounds
    else:
        xmin, ymin, xmax, ymax = bounds

    s = hex_size

    # Hexagon spacing
    dx = 3 * s / 2
    dy = math.sqrt(3) * s

    # Expand bounds slightly to ensure complete coverage
    xmin -= 2 * s
    ymin -= dy
    xmax += 2 * s
    ymax += dy

    hexagons = []

    col = 0
    x = xmin

    while x < xmax:
        y_offset = dy / 2 if col % 2 else 0
        y = ymin + y_offset

        while y < ymax:
            hexagon = Polygon([
                (x - s, y),
                (x - s / 2, y + dy / 2),
                (x + s / 2, y + dy / 2),
                (x + s, y),
                (x + s / 2, y - dy / 2),
                (x - s / 2, y - dy / 2),
            ])
            hexagons.append(hexagon)
            y += dy

        x += dx
        col += 1

    grid = gpd.GeoDataFrame(
        geometry=hexagons,
        crs=crs,
    )

    if overlap:
        if gdf is None:
            raise ValueError("'gdf' must be provided when overlap=True.")

        grid = (
            grid.sjoin(
                gdf,
                how="inner",
                predicate="intersects",
            )
            .drop_duplicates(subset="geometry")
            [["geometry"]]
            .reset_index(drop=True)
        )

    grid = reassign_grid_id(grid)
    grid["area_ha"] = (grid.area / 10_000).round(2)

    return grid.to_crs("EPSG:4326")

def style_function(feature):
    gid = feature["properties"]["grid_id"]

    if gid in st.session_state.selected_hazard_grids:
        return {
            "fillColor": "red",
            "color": "red",
            "weight": 1,
            "fillOpacity": 0.4,
        }
    elif gid in st.session_state.selected_safety_grids:
        return {
            "fillColor": "green",
            "color": "green",
            "weight": 1,
            "fillOpacity": 0.4,
        }
    return {
        "fillColor": "#ffff00",
        "color": "#636363",
        "weight": 0.5,
        "fillOpacity": 0.1,
    }