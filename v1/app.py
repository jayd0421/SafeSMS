import streamlit as st
import folium
from streamlit_folium import st_folium
import v1.functions as f

st.set_page_config(page_title='SafeSMS Salzburg', layout='wide')
st.title("SafeSMS Salzburg")
# st.divider()

if "selected_hazard_grids" not in st.session_state:
    st.session_state.selected_hazard_grids = []
    
if "selected_safety_grids" not in st.session_state:
    st.session_state.selected_safety_grids = []
    
if "grid_type" not in st.session_state:
    st.session_state.grid_type = "Hazard"

send_tab, receive_tab = st.tabs(['Sender', 'Receiver'])

with send_tab:
    city_col, grids_col, grid_type_col = st.columns([3, 1, 1])
    with city_col:
        city = st.text_input("Enter City")
        
    add_roads = st.checkbox("Yes")
        
    
    CENTER = (47.79752787718583, 13.046576195224025)
    m = folium.Map(location=CENTER, zoom_start=12)
    
    # city = "Salzburg, Austria"
    if len(city) != 0:
        
        city_gdf = f.get_city_boundaries(city)
        
        bounds = [[city_gdf.geometry.bounds.miny.min(), city_gdf.geometry.bounds.minx.min()],
          [city_gdf.geometry.bounds.maxy.max(), city_gdf.geometry.bounds.maxx.max()]]
        
        m.fit_bounds(bounds)
        
        
        folium.GeoJson(
            city_gdf,
            name=f"Boundary",
            style_function=lambda feature: {
                "color": "blue",
                "weight": 2,
            },
            # tooltip=folium.GeoJsonTooltip(fields=["name"], aliases=["City:"])
        ).add_to(m)

        with st.spinner("Fetching road network", show_time=True):
            if add_roads:
                city_gdf_utm = city_gdf.to_crs(3857)
                city_area_ha = city_gdf_utm.area / 10000
                
                if city_area_ha[0] > 150000:
                    st.warning(f'City area is {city_area_ha[0]:.2f} Ha. \
                               Choose a city smaller than 150,000 Ha to view road network.')
                
                else:
                    roads_gdf = f.get_city_road_network(city)
                    folium.GeoJson(
                        roads_gdf,
                        name=f"{city}",
                        # tooltip=folium.GeoJsonTooltip(fields=["name"], aliases=["City:"])
                    ).add_to(m)
                    
        # grid = create_grid(city_gdf, n_cells=75, overlap=True)
        with grids_col:
            grid_length = st.number_input("Grid side length", value=400, step=50)
        grid = f.create_hex_grid(city_gdf, hex_size=grid_length, overlap=True)
        
        n_grids_col, grid_size_col, sel_hazard_cells_col, sel_safety_zones_col = st.columns([1, 1, 1, 1])
        n_grids_col.metric("# Grids", value=len(grid), border=True)
        grid_size_col.metric("Grid Area (Ha)", value=(round(grid.area_ha.mean())), border=True)
        
        sel_hazard_cells_col.metric("# Hazard Zones", value=len(st.session_state.selected_hazard_grids), border=True)
        sel_safety_zones_col.metric("# Safety Zones", value=len(st.session_state.selected_safety_grids), border=True)
        
        with grid_type_col:
            grid_type = st.radio("Grid type", options=["Hazard", "Safety"], index=0, horizontal=True)
        if grid_type == "Safety":
            st.session_state.grid_type = "Safety"
        else:
            st.session_state.grid_type = "Hazard"
        
        hazard_ids = ",".join(map(str, st.session_state.selected_hazard_grids))
        safety_ids = ",".join(map(str, st.session_state.selected_safety_grids))
        
        sms_code = f"H:{hazard_ids}|S:{safety_ids}"
        st.write(sms_code)
        st.write(f"{len(sms_code)}/160 characters") 
        
        folium.GeoJson(
            grid,
            name=f"Grid",
            style_function=f.style_function,
            # style_function=lambda feature: {
            #     "fillColor": "#ffff00",
            #     "fillOpacity": 0.1,
            #     "color": "black",
            #     "weight": 0.5,
            # },
            highlight_function=lambda feature: {
                # "weight": 3,
                "color": "red",
                "fillOpacity": 0.5,
            },
            tooltip=folium.GeoJsonTooltip(
                fields=["grid_id", "area_ha"], 
                aliases=["ID", "Area (ha)"],            
                style="""
                    background-color: #F0EFEF;
                    border-radius: 3px;
                    box-shadow: 3px;
                    font-size: 12px
                """
            )
        ).add_to(m)
        
    selected_grids = []
    folium.LayerControl().add_to(m)
    output = st_folium(m, height=550, use_container_width=True, key="emap")

    if output.get("last_active_drawing"):
        props = output["last_active_drawing"]["properties"]
        grid_id = props["grid_id"]

        if st.session_state.grid_type == "Hazard":
            if grid_id in st.session_state.selected_safety_grids:
                st.session_state.selected_safety_grids.remove(grid_id)
            if grid_id in st.session_state.selected_hazard_grids:
                st.session_state.selected_hazard_grids.remove(grid_id)
            else:
                st.session_state.selected_hazard_grids.append(grid_id)
        else:
            if grid_id in st.session_state.selected_hazard_grids:
                st.session_state.selected_hazard_grids.remove(grid_id)
            if grid_id in st.session_state.selected_safety_grids:
                st.session_state.selected_safety_grids.remove(grid_id)
            else:
                st.session_state.selected_safety_grids.append(grid_id)
    st.session_state
      

with receive_tab:
    st.write("Click the map to place the shelter marker")
    