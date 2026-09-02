import streamlit as st
import utils.vector as v

def show_optional_image(image_path, fallback_html, caption=None):
    """Function to display an optional local image

    This function displays a local image when the file exists and renders
    fallback HTML when the image is not available.

    Parameters
    ----------
    image_path : pathlib.Path
        The path to the image file that should be displayed.
    fallback_html : str
        The HTML content to render when the image file is missing.
    caption : str, optional
        The caption to show below the image.

    Returns
    -------
    None
        This function renders content directly in Streamlit.
    """
    if image_path.exists():
        st.image(str(image_path), caption=caption, use_container_width=True)
    else:
        st.markdown(fallback_html, unsafe_allow_html=True)


def is_offline_simulation():
    """Function to check whether offline simulation is active

    This function reads the Streamlit session state and checks whether the
    selected app mode is the offline simulation mode.

    Returns
    -------
    bool
        True when offline simulation mode is selected, otherwise False.
    """
    return st.session_state.app_mode == "Offline simulation"


def offline_config_key(city, grid_size):
    """Function to create an offline preparation key

    This function creates a stable key from the selected city and grid size so
    the app can detect whether prepared offline layers match the current setup.

    Parameters
    ----------
    city : str
        The selected city or place name.
    grid_size : int or float
        The configured hexagonal grid size.

    Returns
    -------
    str
        The combined city and grid-size key.
    """
    return f"{city}|{grid_size}"


def reset_offline_preparation():
    """Function to reset offline preparation state

    This function clears the offline simulation preparation flags when the app
    mode, city, or grid configuration changes.

    Returns
    -------
    None
        This function updates Streamlit session state.
    """
    st.session_state.offline_layers_prepared = False
    st.session_state.offline_prepared_config = None
    st.session_state.offline_layer_status = {
        "City boundary": False,
        "Grid system": False,
        "Road network": False,
        "Basemap / tiles": False,
    }

def prepare_offline_layers(city, grid_size):
    """Function to prepare simulated offline layers

    This function loads the city boundary, grid, and road network, then records
    whether each layer is ready for the offline simulation workflow.

    Parameters
    ----------
    city : str
        The selected city or place name.
    grid_size : int or float
        The configured hexagonal grid size.

    Returns
    -------
    None
        This function updates Streamlit session state with preparation status.
    """
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
    """Function to render offline layer status

    This function displays the current preparation status for each simulated
    offline layer in the Streamlit interface.

    Returns
    -------
    None
        This function renders markdown directly in Streamlit.
    """
    for label, ready in st.session_state.offline_layer_status.items():
        state = "ready" if ready else "pending"
        st.markdown(f"- **{label}:** {state}")


def render_mode_status():
    """Function to render the selected app mode

    This function displays a compact Streamlit status message describing
    whether the app is in online demo mode or offline simulation mode.

    Returns
    -------
    None
        This function renders an informational message directly in Streamlit.
    """
    if is_offline_simulation():
        st.info("Offline simulation mode")
    else:
        st.info("Online demo mode.")
