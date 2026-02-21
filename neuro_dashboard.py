import os
import tempfile
from io import BytesIO

import requests
import streamlit as st

try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None

try:
    import docx2txt
except Exception:
    docx2txt = None

try:
    api_from_secrets = st.secrets["API_URL"]
except Exception:
    api_from_secrets = None

API = (api_from_secrets or os.getenv("API_URL") or "http://127.0.0.1:8000").rstrip("/")


def extract_uploaded_text(uploaded_file) -> str:
    if not uploaded_file:
        return ""

    ext = os.path.splitext(uploaded_file.name.lower())[1]
    raw = uploaded_file.getvalue()

    if ext in (".txt", ".md"):
        return raw.decode("utf-8", errors="ignore")

    if ext == ".pdf":
        if PdfReader is None:
            st.warning("PDF parser not installed. Add pypdf to requirements.")
            return ""
        reader = PdfReader(BytesIO(raw))
        parts = []
        for page in reader.pages:
            parts.append(page.extract_text() or "")
        return "\n".join(parts).strip()

    if ext == ".docx":
        if docx2txt is None:
            st.warning("DOCX parser not installed. Add docx2txt to requirements.")
            return ""
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
                tmp.write(raw)
                temp_path = tmp.name
            return (docx2txt.process(temp_path) or "").strip()
        finally:
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)

    st.warning("Unsupported file format.")
    return ""


def send_study_question(question: str):
    st.session_state.study_chat_history.append({"role": "user", "message": question})
    with st.chat_message("user"):
        st.write(question)

    try:
        resp = requests.post(
            f"{API}/study/chat",
            json={
                "question": question,
                "text": st.session_state.get("study_text", ""),
            },
            timeout=20,
        )
        if resp.ok:
            reply = resp.json().get("reply", "I could not generate a study response right now.")
        else:
            reply = "Study assistant is unavailable right now."
    except requests.RequestException:
        reply = "Could not reach study assistant. Try again."

    st.session_state.study_chat_history.append({"role": "assistant", "message": reply})
    with st.chat_message("assistant"):
        st.write(reply)


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
    role = st.radio("Who is using NeuroLens?", ["Parent / Caregiver", "Child"])
    if st.button("Continue"):
        st.session_state.role = role
        st.rerun()

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

else:
    st.title("Child View")

    mode_label = st.selectbox("Comfort Mode", ["Calm", "Focus / Study", "Neutral"])
    mode_api = {"Calm": "Calm", "Focus / Study": "Focus", "Neutral": "Neutral"}[mode_label]

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
        "Focus / Study": {
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
    theme = mode_theme[mode_label]

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
        requests.post(f"{API}/set-child-mode", params={"mode": mode_api}, timeout=5)
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

    if mode_label == "Focus / Study":
        st.subheader("Focus / Study Mode")
        st.caption("Upload study material or paste text, then ask the assistant to summarize or explain.")

        if "study_text" not in st.session_state:
            st.session_state.study_text = ""
        if "study_highlights" not in st.session_state:
            st.session_state.study_highlights = []
        if "study_chat_history" not in st.session_state:
            st.session_state.study_chat_history = []

        uploaded_file = st.file_uploader(
            "Upload document",
            type=["txt", "md", "pdf", "docx"],
            help="Accepted: TXT, MD, PDF, DOCX",
        )
        pasted_text = st.text_area("Or paste study text", height=180)

        if st.button("Use This Material"):
            extracted = extract_uploaded_text(uploaded_file)
            final_text = "\n\n".join([t for t in [pasted_text.strip(), extracted.strip()] if t]).strip()
            st.session_state.study_text = final_text

            if not final_text:
                st.warning("Please upload a document or paste some text first.")
            else:
                try:
                    resp = requests.post(
                        f"{API}/study/highlights",
                        json={"text": final_text},
                        timeout=20,
                    )
                    if resp.ok:
                        st.session_state.study_highlights = resp.json().get("highlights", [])
                    else:
                        st.session_state.study_highlights = []
                        st.warning("Could not generate highlights right now.")
                except requests.RequestException:
                    st.session_state.study_highlights = []
                    st.warning("Could not contact backend for highlights.")

        if st.session_state.study_text:
            st.success(f"Study material loaded ({len(st.session_state.study_text)} characters).")

        if st.session_state.study_highlights:
            st.markdown("**Important points**")
            for point in st.session_state.study_highlights:
                st.write(f"- {point}")

        st.markdown("---")
        st.subheader("Study Assistant")

        for entry in st.session_state.study_chat_history:
            with st.chat_message(entry["role"]):
                st.write(entry["message"])

        study_prompts = [
            "Summarize this material in simple points.",
            "Explain the toughest topic in easy words.",
            "Ask me 5 quick quiz questions from this.",
        ]
        cols = st.columns(len(study_prompts))
        for i, p in enumerate(study_prompts):
            if cols[i].button(p, key=f"study_prompt_{i}"):
                send_study_question(p)

        study_msg = st.chat_input(
            "Ask about your study material...",
            key="study_chat_input",
        )
        if study_msg:
            send_study_question(study_msg)

    else:
        st.subheader("NeuroLens Companion")
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []

        for entry in st.session_state.chat_history:
            with st.chat_message(entry["role"]):
                st.write(entry["message"])

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

        sample_prompts = [
            "I'm feeling sad and don't know why.",
            "I feel restless and distracted.",
            "I'm nervous about school tomorrow.",
        ]
        cols = st.columns(len(sample_prompts))
        for i, p in enumerate(sample_prompts):
            if cols[i].button(p, key=f"sample_{i}"):
                send_user_message(p)

        user_msg = st.chat_input("Tell me how you're feeling...", key="companion_chat_input")
        if user_msg:
            send_user_message(user_msg)

    if st.button("Switch User"):
        del st.session_state.role
        st.rerun()
