import streamlit as st
from streamlit_drawable_canvas import st_canvas
import requests
import base64
import json
import os
from PIL import Image
import numpy as np

# --- 1. CORE DATA ENGINE ---
def load_curriculum():
    with open('curriculum.json', 'r') as f:
        return json.load(f)['curriculum']

def get_profile(name):
    path = f"{name.lower()}_vault.json"
    if os.path.exists(path):
        with open(path, 'r') as f: return json.load(f)
    return {
        "name": name, "drops": 100, "week_idx": 0, "active_ink": "#000000",
        "xp": {"precision": 50, "logic": 50, "grit": 50},
        "history": []
    }

def save_profile(data):
    with open(f"{data['name'].lower()}_vault.json", 'w') as f: json.dump(data, f)

# --- 2. VISION RELAY (HOLY SHEEP) ---
def analyze_scribe_work(image_data):
    """Sends handwriting to Gemini 3.1 via Holy Sheep for OCR and Grading."""
    buffered = io.BytesIO()
    img = Image.fromarray(image_data.astype('uint8'), 'RGBA')
    img.convert("RGB").save(buffered, format="JPEG")
    encoded_img = base64.b64encode(buffered.getvalue()).decode('utf-8')
    
    headers = {"Authorization": f"Bearer {st.secrets['HS_API_KEY']}"}
    payload = {
        "model": "gemini-3.1-flash-image-preview",
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": "OCR this handwriting. Correct the spelling/grammar. Rate 1-100 on alignment. Return JSON: {'original': '...', 'corrected': '...', 'score': 85}"},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_img}"}}
            ]
        }],
        "response_format": {"type": "json_object"}
    }
    
    try:
        r = requests.post(f"{st.secrets['HS_BASE_URL']}/chat/completions", json=payload, headers=headers)
        return json.loads(r.json()['choices'][0]['message']['content'])
    except:
        return {"original": "Error", "corrected": "Try again", "score": 50}

# --- 3. UI & AUTH ---
st.set_page_config(page_title="The Thinking Chest", layout="wide")
curr = load_curriculum()

# Teacher's Desk Authentication
if "teacher_auth" not in st.session_state: st.session_state.teacher_auth = False
with st.sidebar.expander("🔐 Teacher's Desk"):
    if not st.session_state.teacher_auth:
        pw = st.text_input("Coordinator Access", type="password")
        if pw == "AXIS2026": st.session_state.teacher_auth = True; st.rerun()
    else:
        st.write("✅ Authenticated")
        if st.button("Logout"): st.session_state.teacher_auth = False; st.rerun()

# User Selection
name = st.sidebar.radio("Identify Scribe:", ["Ollie", "Liam"])
user = get_profile(name)

# --- 4. TEACHER ANALYTICS VIEW ---
if st.session_state.teacher_auth:
    st.header("📊 Coordinator Analytics")
    cols = st.columns(2)
    for i, scribe in enumerate(["Ollie", "Liam"]):
        data = get_profile(scribe)
        with cols[i]:
            st.subheader(f"Scribe: {scribe}")
            st.metric("Level", data['week_idx'] + 1)
            st.metric("Precision XP", f"{data['xp']['precision']}%")
            st.progress(data['xp']['precision'] / 100)

# --- 5. THE QUEST ENGINE ---
st.title(f"🧙‍♂️ Level {user['week_idx'] + 1}: {curr[user['week_idx']]['skill']}")
active_week = curr[user['week_idx']]

# Path Choice
col_l, col_r = st.columns(2)
with col_l:
    if st.button(f"🧠 LOGIC: {active_week['choices']['logic']['title']}"): st.session_state.choice = 'logic'
with col_r:
    if st.button(f"🎨 CREATIVE: {active_week['choices']['creative']['title']}"): st.session_state.choice = 'creative'

if 'choice' in st.session_state:
    selected = active_week['choices'][st.session_state.choice]
    st.info(f"**QUEST:** {selected['prompt']}")
    
    # CSS for Dotted Font Overlay & Lines
    lh = 50 if user['xp']['precision'] < 75 else 40
    ghost = st.session_state.get("ghost_text", "")
    
    st.markdown(f"""
        <style>
        @font-face {{ font-family: 'SchoolDots'; src: url('fonts/school_dots.ttf'); }}
        .stCanvas {{ 
            border: 4px solid #31333F; 
            background-image: linear-gradient(#e1e1e1 2px, transparent 1px);
            background-size: 100% {lh}px;
            position: relative;
        }}
        .stCanvas::before {{
            content: "{ghost}";
            font-family: 'SchoolDots', sans-serif;
            font-size: {lh - 5}px;
            color: rgba(0,0,0,0.2);
            position: absolute; top: 10px; left: 10px;
            pointer-events: none; white-space: pre-wrap;
        }}
        </style>
    """, unsafe_allow_html=True)

    # Drawing Canvas
    import io
    canvas_result = st_canvas(
        stroke_width=3, stroke_color=user['active_ink'],
        background_color="#ffffff", height=400, key=f"{name}_w{user['week_idx']}"
    )

    # ACTION BUTTONS
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔍 Analyze Handwriting"):
            if canvas_result.image_data is not None:
                with st.spinner("Gemini is auditing your ink..."):
                    result = analyze_scribe_work(canvas_result.image_data)
                    st.session_state.ghost_text = result['corrected']
                    st.session_state.last_score = result['score']
                    st.rerun()
    
    with c2:
        if "last_score" in st.session_state:
            st.write(f"**Penmanship Score:** {st.session_state.last_score}%")
            if st.button("✨ Seal Chest & Level Up"):
                user['xp']['precision'] = (user['xp']['precision'] + st.session_state.last_score) // 2
                user['week_idx'] += 1
                user['drops'] += 50
                save_profile(user)
                del st.session_state.choice
                if "ghost_text" in st.session_state: del st.session_state.ghost_text
                st.balloons()
                st.rerun()