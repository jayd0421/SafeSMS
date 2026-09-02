import streamlit as st
import utils.vector as v

def show_optional_image(image_path, fallback_html, caption=None):
    if image_path.exists():
        st.image(str(image_path), caption=caption, use_container_width=True)
    else:
        st.markdown(fallback_html, unsafe_allow_html=True)


def is_offline_simulation():
    return st.session_state.app_mode == "Offline simulation"


def offline_config_key(city, grid_size):
    return f"{city}|{grid_size}"


def reset_offline_preparation():
    st.session_state.offline_layers_prepared = False
    st.session_state.offline_prepared_config = None
    st.session_state.offline_layer_status = {
        "City boundary": False,
        "Grid system": False,
        "Road network": False,
        "Basemap / tiles": False,
    }

def prepare_offline_layers(city, grid_size):
    boundary, grid = v.get_city_grid(city, grid_size)
    road_network = v.get_city_road_network(city)

    st.session_state.offline_layer_status = {
        "City boundary": not boundary.empty,
        "Grid system": not grid.empty,
        "Road network": not road_network.empty,
        "Basemap / tiles": True,
    }
    st.session_state.offline_layers_prepared = all(
        st.session_state.offline_layer_status.values()
    )
    st.session_state.offline_prepared_config = offline_config_key(city, grid_size)


def render_layer_status():
    for label, ready in st.session_state.offline_layer_status.items():
        state = "ready" if ready else "pending"
        st.markdown(f"- **{label}:** {state}")


def render_mode_status():
    if is_offline_simulation():
        st.info("Offline simulation mode")
    else:
        st.info("Online demo mode.")