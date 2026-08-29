import streamlit as st

import mapping as mp
import routing as rt
import sms_code as cd
import vector as v


st.set_page_config(
    page_title="Safe SMS",
    layout="wide",
)

st.title("Safe SMS")


DEFAULT_STATE = {
    "selected_hazard_grids": [],
    "selected_safety_grids": [],
    "user_location": None,
    "grid_type": "Hazard",
    "transport_mode": 0,
    "last_selected_grid": None,
}


for key, value in DEFAULT_STATE.items():

    if key not in st.session_state:
        st.session_state[key] = value



sender_tab, receiver_tab = st.tabs(
    [
        "Sender",
        "Recipient",
    ]
)


with sender_tab:

    col1, col2 = st.columns(
        [1, 4]
    )


    with col1:

        with st.container(
            border=True,
            height=820,
        ):
            city = st.text_input(
                "City",
                value="Salzburg, Austria",
            )

            st.session_state.city = city

            
            boundary = v.get_city_boundaries(
                city
            )

            city_area_sqkm = (
                boundary
                .to_crs("EPSG:3857")
                .area
                .sum()
                / 10_000_000
            )

            city_grid_size = max(
                300,
                round(
                    city_area_sqkm
                ) * 25,
            )

            
            grid_size = st.number_input(
                "Grid Size",
                min_value=300,
                value=int(
                    st.session_state.get(
                        "grid_size",
                        city_grid_size,
                    )
                ),
                step=20,
            )

            st.session_state.grid_size = grid_size

            grid_selection_mode = st.radio(
                "Grid selection mode",
                options=[
                    "User defined",
                    "Autogenerate",
                ],
                index=0,
                horizontal=True
            )
            
            if grid_selection_mode == "User defined":
                grid_type = st.radio(
                    "Grid type",
                    options=[
                        "Hazard",
                        "Safety",
                    ],
                    index=(
                        0
                        if st.session_state.grid_type
                        == "Hazard"
                        else 1
                    ),
                    horizontal=True,
                )

                st.session_state.grid_type = (
                    grid_type
                )

                st.info(
                    f"Select {grid_type.lower()} "
                    "zones by clicking the grid."
                )
                
            else:
                no_hazard_col, no_safety_col = st.columns([1, 1])

                with no_hazard_col:
                    no_hazard_grids = st.number_input(
                        "# Hazard Grids",
                        min_value=4,
                        value=40,
                        step=2,
                    )

                with no_safety_col:
                    no_safety_grids = st.number_input(
                        "# Safety Grids",
                        min_value=2,
                        value=5,
                        step=2,
                    )

                generate_grids = st.button(
                    "Generate Grid Zones",
                    type="primary",
                    width="stretch",
                )


            st.divider()
            metric_col1, metric_col2 = (
                st.columns(2)
            )

            metric_col1.metric(
                label="HAZARD ZONES",
                value=len(
                    st.session_state
                    .selected_hazard_grids
                ),
                border=True,
            )

            metric_col2.metric(
                label="SAFE ZONES",
                value=len(
                    st.session_state
                    .selected_safety_grids
                ),
                border=True,
            )

            
            if (
                st.session_state
                .selected_hazard_grids
                or
                st.session_state
                .selected_safety_grids
            ):

                st.divider()

                st.write(
                    "Copy code below and paste "
                    "in Recipient Tab"
                )

                cd.encode_sms()


    with col2:
        with st.container(
            border=True,
            height=820,
        ):

            city_map = mp.City(
                city,
                grid_size,
                key="smap",
            )

            city_map.add_boundary_to_map()

            city_map.add_grid_to_map(
                show_background=True,
                interactive=True,
            )

            map_data = city_map.add_map(
                returned_objects=[
                    "last_active_drawing",
                    "bounds",
                    "zoom",
                ]
            )
            
            if grid_selection_mode == "User defined":
                
                st.dataframe(city_map.get_city_grid())
                mp.process_grid_click(
                    map_data,
                    grid_type,
                )
                
            else:
                grid = city_map.get_city_grid()

                if generate_grids:
                    mp.autogenerate_selected_grids(
                        no_hazard_grids,
                        no_safety_grids,
                        grid,
                    )
                    st.rerun()


with receiver_tab:

    col1, col2 = st.columns(
        [2, 5]
    )


    with col1:

        with st.container(
            border=True,
            height=820,
        ):

            
            st.code(
                st.session_state.city,
                language="python",
            )

            
            sms_payload = st.text_area(
                "Paste SMS Code",
                value=None,
                height=120,
            )

            decoded = cd.decode_sms(
                sms_payload
            )

            receiver_hazard_grids = (
                decoded["hazard"]
            )

            receiver_safety_grids = (
                decoded["safety"]
            )

            

            st.write(
                "User location"
            )
            if (
                st.session_state.user_location
                is None
            ):
                
                st.info(
                    "Click the map to set "
                    "the user location."
                )

            else:

                st.code(
                    f"{st.session_state.user_location[0]:.6f}, "
                    f"{st.session_state.user_location[1]:.6f}",
                    language="python",
                )
            
            st.write(
                "Transport Mode"
            )

            option_map = {
                0: ":material/directions_car:",
                1: ":material/directions_bike:",
                2: ":material/directions_walk:",
            }

            selected_transport_mode = (
                st.segmented_control(
                    "Transport mode",
                    options=option_map.keys(),
                    format_func=lambda option:
                        option_map[option],
                    default=0,
                    label_visibility="collapsed",
                    width="stretch",
                )
            )

            if selected_transport_mode is not None:
                st.session_state.transport_mode = selected_transport_mode

            
            if st.session_state.user_location is not None:
                st.divider()

                distance_col, time_col = st.columns(2)

                distance_metric = distance_col.empty()

                time_metric = (
                    time_col.empty()
                )

                distance_metric.metric(
                    label="DISTANCE",
                    value="N/A",
                    border=True,
                )

                time_metric.metric(
                    label="EST. TIME",
                    value="N/A",
                    border=True,
                )

            
            st.divider()
            blocked_col, area_col = st.columns(2)

            blocked_metric = blocked_col.empty()

            affected_area_metric = area_col.empty()

            blocked_metric.metric(
                label="BLOCKED ZONES",
                value=len(receiver_hazard_grids),
                border=True,
            )

            _, grids = v.get_city_grid(city, grid_size)
            grids_area_sqkm = (
                grids
                .head(1)
                .to_crs("EPSG:3857")
                .area
                .sum()
                / 10_000
            )
            
            affected_area_metric.metric(
                label="AFFECTED AREA",
                value=f"{round(grids_area_sqkm, 2)} ha",
                border=True,
            )


    with col2:
        # with st.container(border=True, height=820):
            # city_map = mp.City(
            #     st.session_state.city,
            #     st.session_state.grid_size,
            #     key="rmap",
            # )

            # previous_hazards = st.session_state.selected_hazard_grids
            # previous_safety = st.session_state.selected_safety_grids
            # st.session_state.selected_hazard_grids = receiver_hazard_grids
            # st.session_state.selected_safety_grids = receiver_safety_grids
            
            # city_map.add_boundary_to_map()

            # city_map.add_grid_to_map(
            #     show_background=False,
            #     interactive=False,
            #     hazard_ids=receiver_hazard_grids,
            #     safety_ids=receiver_safety_grids,
            # )
            
            # city_map.add_marker(
            #     st.session_state.user_location,
            #     "User location",
            # )
            
            # map_data = city_map.add_map(
            #     returned_objects=["last_clicked", "bounds", "zoom"]
            # )
            
            # if (
            #     map_data
            #     and map_data.get(
            #         "last_clicked"
            #     )
            # ):

            #     clicked = map_data["last_clicked"]

            #     next_location = [clicked["lat"], clicked["lng"],]

            #     if (next_location
            #         != st.session_state.user_location
            #     ):

            #         st.session_state.user_location = (
            #             next_location
            #         )

            #         st.rerun()
            
            # route_result = None
            
            # if (
            #     st.session_state.user_location
            #     is not None
            #     and receiver_safety_grids
            # ):
            #     with st.spinner(
            #         "Calculating routes",
            #         show_time=True,
            #     ):
                    
            #         route_result = rt.build_routes(
            #             st.session_state.city,
            #             city_map.grid,
            #             receiver_hazard_grids,
            #             receiver_safety_grids,
            #             st.session_state.user_location,
            #             st.session_state.transport_mode,
            #         )


            #     if route_result["closest_safety_grid"] is not None:
            #         safety_point = route_result["closest_safety_grid"].geometry.representative_point()
            #         city_map.add_safety_marker(
            #             [safety_point.y, safety_point.x],
            #             f"Closest safety grid #{route_result['closest_safety_grid']['grid_id']}",
            #         )

            #     city_map.add_route_to_map(
            #         route_result["shortest_route"],
            #         "Shortest route",
            #         "red",
            #         opacity=0.45,
            #         dash_array="8, 8",
            #     )
            #     city_map.add_route_to_map(
            #         route_result["recommended_route"],
            #         "Recommended route",
            #         "green",
            #         opacity=0.9,
            #     )

            # city_map.add_marker(st.session_state.user_location, "User location")
            # city_map.add_legend(st.session_state.user_location)
            # map_data = city_map.add_map(returned_objects=["last_clicked"])

            # # st.session_state.selected_hazard_grids = previous_hazards
            # # st.session_state.selected_safety_grids = previous_safety

            # if map_data and map_data.get("last_clicked"):
            #     clicked = map_data["last_clicked"]
            #     next_user_location = [clicked["lat"], clicked["lng"]]
            #     if next_user_location != st.session_state.user_location:
            #         st.session_state.user_location = next_user_location
            #         st.rerun()

            # if route_result and route_result["error"]:
            #     st.warning(route_result["error"])
            # elif route_result:
            #     shortest_length = rt.route_length(route_result["shortest_route"])
            #     recommended_length = rt.route_length(route_result["recommended_route"])
            #     display_route = (
            #         route_result["recommended_route"]
            #         if route_result["recommended_route"] is not None
            #         else route_result["shortest_route"]
            #     )

            #     distance_metric.metric(
            #         label="DISTANCE",
            #         value=rt.format_distance(display_route),
            #         border=True,
            #     )
            #     time_metric.metric(
            #         label="EST. TIME",
            #         value=rt.format_time(display_route, st.session_state.transport_mode),
            #         border=True,
            #     )

            #     # metric_cols = st.columns(2)
            #     # metric_cols[0].metric(
            #     #     "Shortest route",
            #     #     "N/A" if shortest_length is None else f"{shortest_length / 1000:.2f} km",
            #     #     border=True,
            #     # )
            #     # metric_cols[1].metric(
            #     #     "Recommended route",
            #     #     "N/A" if recommended_length is None else f"{recommended_length / 1000:.2f} km",
            #     #     border=True,
            #     # )

            # hazard_grid = rt.get_selected_grid(city_map.grid, receiver_hazard_grids)
            # affected_area = hazard_grid["area_ha"].sum()*0.01 if not hazard_grid.empty else 0
            # affected_area_metric.metric(
            #     label="AFFECTED AREA",
            #     value=f"{affected_area:.1f} sqkm",
            #     border=True,
            # )


        with st.container(border=True, height=820):
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

                if route_result["closest_safety_grid"] is not None:
                    safety_point = route_result["closest_safety_grid"].geometry.representative_point()
                    city_map.add_safety_marker(
                        [safety_point.y, safety_point.x],
                        f"Closest safety grid #{route_result['closest_safety_grid']['grid_id']}",
                    )

                city_map.add_route_to_map(
                    route_result["shortest_route"],
                    "Shortest route",
                    "red",
                    opacity=0.45,
                    dash_array="8, 8",
                )
                city_map.add_route_to_map(
                    route_result["recommended_route"],
                    "Recommended route",
                    "green",
                    opacity=0.9,
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
                    label="DISTANCE",
                    value=rt.format_distance(display_route),
                    border=True,
                )
                time_metric.metric(
                    label="EST. TIME",
                    value=rt.format_time(display_route, st.session_state.transport_mode),
                    border=True,
                )

                metric_cols = st.columns(2)
                metric_cols[0].metric(
                    "Shortest route",
                    "N/A" if shortest_length is None else f"{shortest_length / 1000:.2f} km",
                    border=True,
                )
                metric_cols[1].metric(
                    "Recommended route",
                    "N/A" if recommended_length is None else f"{recommended_length / 1000:.2f} km",
                    border=True,
                )

            hazard_grid = rt.get_selected_grid(city_map.grid, receiver_hazard_grids)
            affected_area = hazard_grid["area_ha"].sum()*0.01 if not hazard_grid.empty else 0
            affected_area_metric.metric(
                label="AFFECTED AREA",
                value=f"{affected_area:.1f} sqkm",
                border=True,
            )
