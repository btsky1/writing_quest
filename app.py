import streamlit as st
from streamlit_drawable_canvas import st_canvas
import requests
import base64
import json
import os
import io
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
        "name": name, 
        "drops": 100, 
        "week_idx": 0, 
        "active_ink": "#000000",
        "xp": {"precision": 50, "logic": 50, "grit": 50},
        "unlocked_inks": ["#000000"]
    }

def save_profile(data):
    with open(f"{data['name'].lower()}_vault.json", 'w') as f: json.dump(data, f)

if not os.path.exists("gallery"):
    os.makedirs("gallery")

# --- 2. VISION RELAY (HOLY SHEEP) ---
def analyze_scribe_work(image_data):
    buffered = io.BytesIO()
    img = Image.fromarray(image_data.astype('uint8'), 'RGBA')
    img.convert("RGB").save(buffered, format="JPEG")
    encoded_img = base64.b64encode(buffered.getvalue()).decode('utf-8')
    
    headers = {
        "Authorization": f"Bearer {st.secrets['HS_API_KEY']}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "gemini-3.1-flash-image-preview",
        "messages": [{
            "role": "user",
            "content": [
                {
                    "type": "text", 
                    "text": """Analyze this student's handwriting. 
                    1. Correct spelling/grammar.
                    2. Give 3 short tips for a child to improve.
                    3. Score 1-100 on penmanship.
                    Return JSON only: {"corrected": "...", "tips": ["...", "...", "..."], "score": 85}"""
                },
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_img}"}}
            ]
        }],
        "response_format": {"type": "json_object"}
    }
    
    try:
        r = requests.post(f"{st.secrets['HS_BASE_URL']}/chat/completions", json=payload, headers=headers)
        return json.loads(r.json()['choices'][0]['message']['content'])
    except Exception:
        return {"corrected": "The Master Scribe is resting. Try again!", "tips": ["Check your internet", "Ensure the photo is clear"], "score": 0}

# --- 3. UI SETUP ---
st.set_page_config(page_title="The Thinking Chest", layout="wide")

if "ghost_text" not in st.session_state: st.session_state.ghost_text = ""
if "advice" not in st.session_state: st.session_state.advice = []
if "last_score" not in st.session_state: st.session_state.last_score = 0
if "teacher_auth" not in st.session_state: st.session_state.teacher_auth = False

curr = load_curriculum()

# Sidebar: HUD & Profiles
name = st.sidebar.radio("Identify Scribe:", ["Ollie", "Liam"])
user = get_profile(name)

st.sidebar.title(f"🏰 {user['name']}'s Vault")
st.sidebar.metric("Ink Drops", f"{user['drops']} 💧")

# Stats Progress
for stat, val in user['xp'].items():
    st.sidebar.caption(f"{stat.capitalize()}: {val}%")
    st.sidebar.progress(val / 100)

# Ink Shop (Mini)
with st.sidebar.expander("🎨 Ink Merchant"):
    inks = {"Midnight": "#000000", "Royal Blue": "#0000ff", "Dragon Red": "#ff0000", "Gold": "#ffd700"}
    for ink_name, hex_code in inks.items():
        if hex_code in user.get('unlocked_inks', ["#000000"]):
            if st.button(f"Use {ink_name}"):
                user['active_ink'] = hex_code
                save_profile(user)
                st.rerun()
        else:
            if st.button(f"Buy {ink_name} (500 💧)"):
                if user['drops'] >= 500:
                    user['drops'] -= 500
                    user['unlocked_inks'].append(hex_code)
                    save_profile(user)
                    st.rerun()

# Teacher's Desk
with st.sidebar.expander("🔐 Teacher's Desk"):
    if not st.session_state.teacher_auth:
        pw = st.text_input("Coordinator Access", type="password")
        if pw == "AXIS2026": 
            st.session_state.teacher_auth = True
            st.rerun()
    else:
        if st.button("Logout"): 
            st.session_state.teacher_auth = False
            st.rerun()

# --- 4. THE QUEST ENGINE ---
st.title(f"🧙‍♂️ Level {user['week_idx'] + 1}: {curr[user['week_idx']]['skill']}")
active_week = curr[user['week_idx']]

if 'choice' not in st.session_state:
    col_l, col_r = st.columns(2)
    with col_l:
        if st.button(f"🧠 LOGIC: {active_week['choices']['logic']['title']}"): 
            st.session_state.choice = 'logic'; st.rerun()
    with col_r:
        if st.button(f"🎨 CREATIVE: {active_week['choices']['creative']['title']}"): 
            st.session_state.choice = 'creative'; st.rerun()

if 'choice' in st.session_state:
    selected = active_week['choices'][st.session_state.choice]
    st.info(f"**QUEST:** {selected['prompt']}")

    if st.session_state.advice:
        with st.expander("📜 Master Scribe's Advice", expanded=True):
            st.subheader(f"Target: {st.session_state.ghost_text}")
            for tip in st.session_state.advice: st.write(f"📍 {tip}")

    # CSS Ghost Logic
    lh = 50 if user['xp']['precision'] < 75 else 40
    clean_ghost = st.session_state.ghost_text.replace('"', '').replace('\n', ' ')
    
    st.markdown(f"""
        <style>
        @font-face {{ 
            font-family: 'SchoolDots'; 
            src: url('https://raw.githubusercontent.com/btsky1/writing_quest/main/fonts/school_dots.ttf'); 
        }}
        .stCanvas {{ 
            border: 4px solid #31333F; 
            background-image: linear-gradient(#e1e1e1 2px, transparent 1px);
            background-size: 100% {lh}px;
            position: relative;
        }}
        .stCanvas::before {{
            content: "{clean_ghost}";
            font-family: 'SchoolDots', 'Courier New', monospace;
            font-size: {lh - 8}px;
            color: rgba(0,0,0,0.2);
            position: absolute; top: 10px; left: 15px;
            pointer-events: none; white-space: pre-wrap;
            z-index: 0;
        }}
        </style>
    """, unsafe_allow_html=True)

    canvas_result = st_canvas(
        stroke_width=3, stroke_color=user['active_ink'],
        background_color="rgba(0,0,0,0)", 
        height=400, key=f"{name}_w{user['week_idx']}_{st.session_state.choice}"
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("🔍 Analyze Handwriting"):
            if canvas_result.image_data is not None:
                with st.spinner("Reviewing..."):
                    result = analyze_scribe_work(canvas_result.image_data)
                    st.session_state.ghost_text = result.get('corrected', '')
                    st.session_state.advice = result.get('tips', [])
                    st.session_state.last_score = result.get('score', 0)
                    st.rerun()
    with c2:
        if st.session_state.last_score > 0:
            if st.button("✨ Seal Chest"):
                if canvas_result.image_data is not None:
                    img = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')
                    img.save(f"gallery/{name.lower()}_lv{user['week_idx']+1}.png")
                
                # Rewards Calculation
                score = st.session_state.last_score
                earned_drops = 75 if score < 85 else 150 # Mastery Bonus
                
                user['xp']['precision'] = (user['xp']['precision'] + score) // 2
                user['drops'] += earned_drops
                user['week_idx'] += 1
                save_profile(user)
                
                st.session_state.ghost_text = ""; st.session_state.advice = []; st.session_state.last_score = 0
                del st.session_state.choice
                st.balloons()
                st.success(f"Chest Sealed! You earned {earned_drops} Ink Drops! 💧")
                st.rerun()
    with c3:
        if st.button("🔄 Abandon"):
            del st.session_state.choice
            st.session_state.ghost_text = ""
            st.rerun()