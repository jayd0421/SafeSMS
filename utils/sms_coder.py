import streamlit as st

def encode_sms():    
    """Function to encode selected grids into an SMS message

    This function reads selected hazard and safety grid IDs from Streamlit
    session state and displays a compact SMS-style message.

    Returns
    -------
    None
        This function renders the encoded SMS message directly in Streamlit.
    """
    hazard_ids = ",".join(map(str, st.session_state.selected_hazard_grids))
    safety_ids = ",".join(map(str, st.session_state.selected_safety_grids))
    
    sms_code = f"FLOODING ALERT!! \nH:{hazard_ids}\nS:{safety_ids}"
    
    st.code(sms_code, language="python", height=65)


def decode_sms(sms_code):
    """Function to decode an SMS grid message

    This function parses a compact SMS-style message and extracts hazard and
    safety grid IDs for use on the recipient map.

    Parameters
    ----------
    sms_code : str
        The SMS-style message containing hazard and safety grid IDs.

    Returns
    -------
    dict
        A dictionary with ``hazard`` and ``safety`` lists of integer grid IDs.
    """
    decoded = {
        "hazard": [],
        "safety": [],
    }

    if not sms_code:
        return decoded

    normalized = sms_code.replace("FLOODING ALERT!! \n", "").replace("\n", "|").replace(" ", "")

    for part in normalized.split("|"):
        if not part or ":" not in part:
            continue

        key, value = part.split(":", 1)
        target = None

        if key.upper() == "H":
            target = "hazard"
        elif key.upper() == "S":
            target = "safety"

        if target is None or not value:
            continue

        decoded[target] = [
            int(item)
            for item in value.split(",")
            if item.strip().isdigit()
        ]

    return decoded
