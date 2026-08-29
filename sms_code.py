import streamlit as st

def encode_sms():    
    hazard_ids = ",".join(map(str, st.session_state.selected_hazard_grids))
    safety_ids = ",".join(map(str, st.session_state.selected_safety_grids))
    
    sms_code = f"H:{hazard_ids}\nS:{safety_ids}"
    
    st.code(sms_code, language="python")


def decode_sms(sms_code):
    decoded = {
        "hazard": [],
        "safety": [],
    }

    if not sms_code:
        return decoded

    normalized = sms_code.replace("\n", "|").replace(" ", "")

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
