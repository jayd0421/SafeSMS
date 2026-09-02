from pathlib import Path

import streamlit as st

import utils.mapping as mp
import utils.description as desc
import utils.routing as rt
import utils.sms_code as cd
import utils.vector as v


BASE_DIR = Path(__file__).resolve().parent
SENDER_SCREENSHOT = BASE_DIR / "data" / "sender.png"
RECIPIENT_SCREENSHOT = BASE_DIR / "data" / "reciever.png"


def show_optional_image(image_path, fallback_html, caption=None):
    if image_path.exists():
        st.image(str(image_path), caption=caption, use_container_width=True)
    else:
        st.markdown(fallback_html, unsafe_allow_html=True)


st.set_page_config(page_title="Safe SMS",layout="wide")

st.title("Safe SMS")

st.markdown(desc.PAGE_STYLES, unsafe_allow_html=True)

# --- Session state defaults ---
DEFAULT_STATE = {
    "page": "home",
    "selected_hazard_grids": [],
    "selected_safety_grids": [],
    "user_location": None,
    "grid_type": "Hazard",
    "transport_mode": 0,
    "last_selected_grid": None
}

for key, value in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = value

# --- HOME PAGE ---
if st.session_state.page == "home":
    st.subheader("Why SafeSMS?")

    st.markdown(desc.HOME_INTRO, unsafe_allow_html=True)
    story_col, image_col = st.columns([3, 2], vertical_alignment="center")
    with story_col:
        st.markdown(desc.HOME_STORY_PRIMARY, unsafe_allow_html=True)

    with image_col:
        st.image(
            desc.EMERGENCY_IMAGE_URL,
            caption=desc.EMERGENCY_IMAGE_CAPTION,
            use_container_width=True,
            link=desc.EMERGENCY_IMAGE_SOURCE_URL,
        )
    
    st.markdown(desc.HOME_STORY_SECONDARY, unsafe_allow_html=True)
    
    if st.button("Next Page   ---→", type='primary', key='b1'):
        st.session_state.page = "instruct"
        st.rerun()

# --- INSTRUCTIONS PAGE ---
if st.session_state.page == "instruct":
    st.subheader("How to use SafeSMS")

    st.markdown(desc.INSTRUCTIONS_INTRO, unsafe_allow_html=True)

    sender_col, recipient_col = st.columns(2)

    with sender_col:
        st.markdown("### Dispatcher / Sender")
        st.markdown(desc.SENDER_GUIDE, unsafe_allow_html=True)
        show_optional_image(
            SENDER_SCREENSHOT,
            desc.SENDER_SCREENSHOT_PLACEHOLDER,
            "Dispatcher / sender workflow screenshot.",
        )

    with recipient_col:
        st.markdown("### Person at Risk / Recipient")
        st.markdown(desc.RECIPIENT_GUIDE, unsafe_allow_html=True)
        show_optional_image(
            RECIPIENT_SCREENSHOT,
            desc.RECIPIENT_SCREENSHOT_PLACEHOLDER,
            "Recipient workflow screenshot.",
        )
        
    st.write("")
    prev_col, next_col = st.columns([13, 1])

    with prev_col:
        if st.button("←----", type='secondary', key='b2'):
            st.session_state.page = "home"
            st.rerun()
    with next_col:       
        if st.button("---→", type='primary', key='b3'):
            st.session_state.page = "prep"
            st.rerun()
        
# --- OFFLINE PREPARATION ---
if st.session_state.page == "prep":
    st.subheader('Offline Preparation')
    input_col, map_col = st.columns([2, 5])

    with input_col:
        with st.container(border=True, height=600):
            city = st.text_input("City", value="Salzburg, Austria")
            st.session_state.city = city
            
            boundary = v.get_city_boundaries(city)

            city_area_sqkm = boundary.to_crs("EPSG:3857").area.sum() / 10_000_000

            city_grid_size = max(300, round(city_area_sqkm) * 25)

            grid_size = st.number_input(
                "Grid Size",
                min_value=300,
                value=int(st.session_state.get("grid_size", city_grid_size)),
                step=20,
            )

            st.session_state.grid_size = grid_size

            st.info("Clicking next will begin preparing the layers for offline use.")
            
            st.write("")
            prev_col, next_col = st.columns([4, 1])

            with prev_col:
                if st.button("←----", type='secondary', key='b4'):
                    st.session_state.page = "instruct"
                    st.rerun()
                    
            with next_col:
                if st.button("---→", type='primary', key='b5'):
                    st.session_state.page = "sender"
                    st.rerun()

    with map_col:
        with st.container(border=True, height=600):
            city_map = mp.City(city, grid_size, key="smap")

            city_map.add_boundary_to_map()

            city_map.add_grid_to_map(show_background=True, interactive=False)
            
            map_data = city_map.add_map()

# --- SENDER ---
if st.session_state.page == "sender":
    st.subheader('Dispatcher: Hazard & Safety Zone Selection')
    input_col, map_col = st.columns([2, 5])

    with input_col:
        with st.container(border=True, height = 600):
            city = st.session_state.city
            
            st.code(city, language="python", height=45)
            
            grid_size = st.session_state.grid_size
            
            st.code(f"Grid Size: {grid_size}", language="python", height = 45)

            grid_selection_mode = st.radio(
                "Grid selection mode",
                options=["User defined", "Autogenerated"],
                index=0, horizontal=True,
                help="Toggle to difne your own grids or automatically generate grid."
            )
            
            if grid_selection_mode == "User defined":
                grid_type = st.radio(
                    "Grid mode",
                    options=["Hazard", "Safety"],
                    index=(0 if st.session_state.grid_type == "Hazard" else 1),
                    horizontal=True, help='Toggle and double-click the grid to select zones.'
                )

                st.session_state.grid_type = grid_type
                
            elif grid_selection_mode == "Autogenerated" :
                no_hazard_col, no_safety_col, submit_col = st.columns([3, 3, 3])

                with no_hazard_col:
                    no_hazard_grids = st.number_input(
                        "# Hazard Grids", min_value=4, value=40, step=2,
                    )

                with no_safety_col:
                    no_safety_grids = st.number_input(
                        "# Safety Grids", min_value=2, value=5, step=2,
                    )

                with submit_col:
                    st.write("")
                    st.write("")
                    generate_grids = st.button("Generate", type="primary", width="stretch")
                    

            # st.divider()
            hazard_metric_col, safety_metric_col = st.columns(2)

            hazard_metric_col.metric(
                label="HAZARD ZONES",
                value=len(st.session_state.selected_hazard_grids),
                border=True, height=100
            )

            safety_metric_col.metric(
                label="SAFE ZONES",
                value=len(st.session_state.selected_safety_grids),
                border=True, height=100
            )

            if st.session_state.selected_hazard_grids or st.session_state.selected_safety_grids:
                st.write("Copy code below and paste in the next tab")

                cd.encode_sms()
        
            prev_col, next_col = st.columns([4, 1])

            with prev_col:
                if st.button("←----", type='secondary'):
                    st.session_state.page = "prep"
                    st.rerun()
                    
            with next_col:
                if st.button("---→", type='primary'):
                    st.session_state.page = "receiver"
                    st.rerun()

    with map_col:
        with st.container(border=True, height=600):
            city_map = mp.City(city, grid_size, key="smap")

            city_map.add_boundary_to_map()

            city_map.add_grid_to_map(show_background=True, interactive=True)

            map_data = city_map.add_map(returned_objects=["last_active_drawing", "bounds", "zoom"])
            
            if grid_selection_mode == "User defined":
                mp.process_grid_click(map_data, grid_type)
                
            else:
                grid = city_map.get_city_grid()
                if generate_grids:
                    st.write("Yess")
                    with st.spinner("Generating Hazard and Safety grids..."):
                        mp.autogenerate_selected_grids(no_hazard_grids, no_safety_grids, grid)
                        st.rerun()
    
# --- RECEIVER ---
if st.session_state.page == "receiver":
    st.subheader('Person at Risk: Navigation to Safety')
    input_col, map_col = st.columns([3, 6])

    with input_col:
        with st.container(border=True, height=600):
            st.code(st.session_state.city, language="python", height=45)

            sms_payload = st.text_area("Paste SMS Code", value=None, height=120)

            decoded = cd.decode_sms(sms_payload)

            receiver_hazard_grids = decoded["hazard"]
            receiver_safety_grids = decoded["safety"]

            st.write("User location")
            
            if st.session_state.user_location is None:
                st.info("Click the map to set the user location.")

            else:
                location_col, cancel_col = st.columns([8, 1])
                
                with location_col:
                    st.code(
                        f"{st.session_state.user_location[0]:.6f}, "
                        f"{st.session_state.user_location[1]:.6f}",
                        language="python", height=40
                    )
                
                with cancel_col:
                    user = st.button("X", type='primary', help="Click twice to re-expand SMS code and remove user location")
                    if user:
                        st.session_state.user_location = None
            
            st.write("Transport Mode")

            option_map = {
                0: ":material/directions_car:",
                1: ":material/directions_bike:",
                2: ":material/directions_walk:",
            }

            selected_transport_mode = st.segmented_control(
                    "Transport mode",
                    options=option_map.keys(),
                    format_func=lambda option: option_map[option],
                    default=st.session_state.transport_mode,
                    label_visibility="collapsed",
                    width="stretch",
                    key='tm'
                )

            if selected_transport_mode is not None:
                st.session_state.transport_mode = selected_transport_mode
            
            if st.session_state.user_location is not None:
                distance_col, time_col = st.columns(2)

                distance_metric = distance_col.empty()
                time_metric = time_col.empty()

                distance_metric.metric(label="RECOMMENDED ROUTE", value="N/A", border=True, height=100)
                time_metric.metric(label="EST. TIME", value="N/A", border=True, height=100)

            blocked_col, area_col = st.columns(2)

            blocked_metric = blocked_col.empty()
            affected_area_metric = area_col.empty()

            blocked_metric.metric(
                label="BLOCKED ZONES", value=len(receiver_hazard_grids),
                border=True, height=100
            )

            _, grids = v.get_city_grid(st.session_state.city, st.session_state.grid_size)
            hazard_grid = rt.get_selected_grids(grids, receiver_hazard_grids)
            affected_area_sqkm = hazard_grid["area_ha"].sum() * 0.01
            
            affected_area_metric.metric(
                label="AFFECTED AREA", value=affected_area_sqkm, 
                border=True, height=100)

            prev_col, route_col = st.columns(2)
            with prev_col:
                if st.button("←----", type='secondary', key='b6'):
                    st.session_state.page = "sender"
                    st.rerun()
            
            route_popover = route_col.empty()


    with map_col:
        with st.container(border=True, height=600):
            grid_size = st.session_state.grid_size
            city_map = mp.City(st.session_state.city, grid_size, key="rmap")

            previous_hazards = st.session_state.selected_hazard_grids
            previous_safety = st.session_state.selected_safety_grids
            
            st.session_state.selected_hazard_grids = receiver_hazard_grids
            st.session_state.selected_safety_grids = receiver_safety_grids

            city_map.add_boundary_to_map()
            city_map.add_grid_to_map(show_background=False, interactive=False)

            route_result = None
            if st.session_state.user_location is not None and receiver_safety_grids:
                with st.spinner("Calculating routes", show_time=True):
                    route_result = rt.build_routes(
                        st.session_state.city,
                        city_map.grid,
                        receiver_hazard_grids,
                        receiver_safety_grids,
                        st.session_state.user_location,
                        st.session_state.transport_mode,
                    )

                if route_result["recommended_route"] is not None:
                    with route_popover:
                        with st.popover("Route details"):
                            st.markdown("#### Route details")

                            for i, (_, row) in enumerate(
                                route_result["recommended_route"].iterrows(),
                                start=1
                            ):
                                street = row["street_name"]
                                length = row["length"]

                                if length >= 1000:
                                    length_text = f"{length / 1000:.1f} km"
                                else:
                                    length_text = f"{length:.0f} m"

                                st.markdown(
                                    f"**{i}. {street}**  \n{length_text}"
                                )

                
                if route_result["closest_safety_grid"] is not None:
                    safety_point = route_result["closest_safety_grid"].geometry.representative_point()
                    city_map.add_safety_marker(
                        [safety_point.y, safety_point.x],
                        f"Closest safety grid #{route_result['closest_safety_grid']['grid_id']}",
                    )

                city_map.add_route_to_map(
                    route_result["shortest_route"],
                    "Shortest route", "red", opacity=0.85,
                    dash_array="8, 8",
                )
                city_map.add_route_to_map(
                    route_result["recommended_route"],
                    "Recommended route", "green", opacity=0.9,
                )

            city_map.add_marker(st.session_state.user_location, "User location")
            city_map.add_legend(st.session_state.user_location)
            map_data = city_map.add_map(returned_objects=["last_clicked"])

            st.session_state.selected_hazard_grids = previous_hazards
            st.session_state.selected_safety_grids = previous_safety

            if map_data and map_data.get("last_clicked"):
                clicked = map_data["last_clicked"]
                next_user_location = [clicked["lat"], clicked["lng"]]
                if next_user_location != st.session_state.user_location:
                    st.session_state.user_location = next_user_location
                    st.rerun()

            if route_result and route_result["error"]:
                st.warning(route_result["error"])
                
            elif route_result:
                shortest_length = rt.route_length(route_result["shortest_route"])
                recommended_length = rt.route_length(route_result["recommended_route"])
                display_route = (
                    route_result["recommended_route"]
                    if route_result["recommended_route"] is not None
                    else route_result["shortest_route"]
                )

                distance_metric.metric(
                    label="RECOMMENED ROUTE",
                    value=rt.format_distance(display_route),
                    border=True, height=100
                )
                time_metric.metric(
                    label="EST. TIME",
                    value=rt.format_time(display_route, st.session_state.transport_mode),
                    border=True, height=100
                )
