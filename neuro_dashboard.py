import streamlit as st
import requests
import os

try:
    api_from_secrets = st.secrets["API_URL"]
except Exception:
    api_from_secrets = None

API = (api_from_secrets or os.getenv("API_URL") or "http://127.0.0.1:8000").rstrip("/")

st.set_page_config(page_title="NeuroLens")

st.markdown(
    """
    <style>
    .reportview-container, .main, header, footer {background-color: #E6E6FA;}
    .stButton>button {background-color: #B57EDC; color: white;}
    </style>
    """,
    unsafe_allow_html=True,
)

if "role" not in st.session_state:

    st.title("NeuroLens")

    role = st.radio("Who is using NeuroLens?",
                    ["Parent / Caregiver", "Child"])

    if st.button("Continue"):
        st.session_state.role = role
        st.rerun()

# ============================================================
# PARENT VIEW
# ============================================================

elif st.session_state.role == "Parent / Caregiver":

    st.title("Parent / Caregiver View")

    st.subheader("Comfort Thresholds")

    brightness_t = st.slider("Brightness Threshold", 0, 100, 50)
    noise_t = st.slider("Noise Threshold", 0, 100, 40)

    if st.button("Apply Thresholds"):
        try:
            requests.post(
                f"{API}/set-thresholds",
                params={"brightness": brightness_t, "noise": noise_t},
                timeout=5,
            )
        except requests.RequestException:
            st.warning("Could not apply thresholds right now.")

    st.markdown("---")
    st.subheader("Environment State")

    try:
        data = requests.get(f"{API}/state", timeout=5).json()

        st.metric("Brightness", f'{data["brightness"]}%')
        st.metric("Noise", f'{data["noise"]} dB')

        if data["exceeded"]:
            st.warning("Warning: values exceed thresholds")

            if st.button("Auto Adjust"):
                try:
                    requests.post(f"{API}/auto-adjust", timeout=5)
                    st.rerun()
                except requests.RequestException:
                    st.warning("Auto-adjust failed. Please try again.")
        else:
            st.success("Values within thresholds")

    except Exception:
        st.error("Backend not reachable")

    if st.button("Switch User"):
        del st.session_state.role
        st.rerun()

# ============================================================
# CHILD VIEW
# ============================================================

else:

    st.title("Child View")

    mode = st.selectbox("Comfort Mode", ["Calm", "Focus", "Neutral"])
    mode_theme = {
        "Calm": {
            "bg": "#EAF7F2",
            "panel": "#D5EFE5",
            "button": "#4C9F84",
            "user_chat": "#CDEBDD",
            "assistant_chat": "#E9F7F1",
            "warning_bg": "#FCE9D9",
            "warning_text": "#8A4B21",
            "info_bg": "#DDF1E9",
            "info_text": "#1F6A4F",
            "success_bg": "#D7F3E4",
            "success_text": "#175A43",
        },
        "Focus": {
            "bg": "#FFF7E8",
            "panel": "#FFE6B8",
            "button": "#D98E04",
            "user_chat": "#FFE0A6",
            "assistant_chat": "#FFF1D6",
            "warning_bg": "#FFE3CC",
            "warning_text": "#8A3E00",
            "info_bg": "#FFF0CC",
            "info_text": "#7A4B00",
            "success_bg": "#FFE9B8",
            "success_text": "#6B4A00",
        },
        "Neutral": {
            "bg": "#F1F2F6",
            "panel": "#DEE1EA",
            "button": "#687086",
            "user_chat": "#D7DCE8",
            "assistant_chat": "#ECEFF5",
            "warning_bg": "#F6E4E4",
            "warning_text": "#7D2E2E",
            "info_bg": "#E4EAF4",
            "info_text": "#304866",
            "success_bg": "#E2F0E6",
            "success_text": "#2F5D3B",
        },
    }
    theme = mode_theme[mode]
    st.markdown(
        f"""
        <style>
        .stApp {{ background-color: {theme["bg"]}; }}
        div[data-testid="stMetric"] {{
            background-color: {theme["panel"]};
            border-radius: 10px;
            padding: 10px;
        }}
        .stButton>button {{
            background-color: {theme["button"]};
            color: white;
            border: none;
        }}
        div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-user"]) {{
            background-color: {theme["user_chat"]};
            border-radius: 12px;
            padding: 6px 10px;
        }}
        div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-assistant"]) {{
            background-color: {theme["assistant_chat"]};
            border-radius: 12px;
            padding: 6px 10px;
        }}
        div[data-baseweb="notification"][kind="warning"] {{
            background-color: {theme["warning_bg"]};
            color: {theme["warning_text"]};
        }}
        div[data-baseweb="notification"][kind="info"] {{
            background-color: {theme["info_bg"]};
            color: {theme["info_text"]};
        }}
        div[data-baseweb="notification"][kind="success"] {{
            background-color: {theme["success_bg"]};
            color: {theme["success_text"]};
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
    try:
        requests.post(f"{API}/set-child-mode", params={"mode": mode}, timeout=5)
    except requests.RequestException:
        st.warning("Could not update mode right now.")

    try:
        data = requests.get(f"{API}/state", timeout=5).json()
        st.metric("Brightness", f'{data["brightness"]}%')
        st.metric("Noise", f'{data["noise"]} dB')

        if data["exceeded"]:
            st.info("Adjusting environment for comfort")
    except requests.RequestException:
        st.warning("Environment state is temporarily unavailable.")

    st.markdown("---")
    st.subheader("NeuroLens Companion")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Render existing messages
    for entry in st.session_state.chat_history:
        with st.chat_message(entry["role"]):
            st.write(entry["message"])

    # ---------- Message Sender ----------
    def send_user_message(msg):

        st.session_state.chat_history.append({"role": "user", "message": msg})

        with st.chat_message("user"):
            st.write(msg)

        try:
            resp = requests.post(f"{API}/chat", json={"message": msg}, timeout=15)

            if resp.ok:
                reply = resp.json().get("reply", "Sorry, I couldn't generate a reply.")
            else:
                reply = "Sorry, the assistant is unavailable."

        except requests.RequestException:
            reply = "Error contacting assistant. Please try again."

        st.session_state.chat_history.append({"role": "assistant", "message": reply})

        with st.chat_message("assistant"):
            st.write(reply)

    # Suggested prompts
    sample_prompts = [
        "I'm feeling sad and don't know why.",
        "I can't focus on my homework.",
        "I'm nervous about school tomorrow.",
    ]

    cols = st.columns(len(sample_prompts))

    for i, p in enumerate(sample_prompts):
        if cols[i].button(p, key=f"sample_{i}"):
            send_user_message(p)

    # Custom input
    user_msg = st.chat_input("Tell me how you're feeling...")

    if user_msg:
        send_user_message(user_msg)

    if st.button("Switch User"):
        del st.session_state.role
        st.rerun()
