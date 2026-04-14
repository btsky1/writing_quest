import streamlit as st
from streamlit_drawable_canvas import st_canvas
import requests, base64, json, os, io
from PIL import Image

# --- 1. CORE DATA ENGINE ---
def load_curriculum():
    with open('curriculum.json', 'r') as f: return json.load(f)['curriculum']

def get_profile(name):
    path = f"{name.lower()}_vault.json"
    if os.path.exists(path):
        with open(path, 'r') as f: return json.load(f)
    return {"name": name, "drops": 100, "week_idx": 0, "active_ink": "#000000", "xp": {"precision": 50, "logic": 50, "grit": 50}, "unlocked_inks": ["#000000"]}

def save_profile(data):
    with open(f"{data['name'].lower()}_vault.json", 'w') as f: json.dump(data, f)

# --- 2. DYNAMIC JOURNAL GENERATOR ---
def get_journal_prompt(user_data, week_data):
    # This creates a unique prompt every time based on their level and current XP
    headers = {"Authorization": f"Bearer {st.secrets['HS_API_KEY']}", "Content-Type": "application/json"}
    payload = {
        "model": "gemini-3.1-flash",
        "messages": [{"role": "system", "content": f"You are a Scribe Master. Create a 1-sentence journal prompt for a 7yo boy. Topic: {week_data['skill']}. Focus: {st.session_state.choice}."}],
    }
    try:
        r = requests.post(f"{st.secrets['HS_BASE_URL']}/chat/completions", json=payload, headers=headers)
        return r.json()['choices'][0]['message']['content']
    except: return week_data['choices'][st.session_state.choice]['prompt']

# --- 3. VISION RELAY (The Gatekeeper) ---
def analyze_scribe_work(image_data):
    buffered = io.BytesIO()
    img = Image.fromarray(image_data.astype('uint8'), 'RGBA')
    img.convert("RGB").save(buffered, format="JPEG")
    encoded_img = base64.b64encode(buffered.getvalue()).decode('utf-8')
    headers = {"Authorization": f"Bearer {st.secrets['HS_API_KEY']}", "Content-Type": "application/json"}
    
    # STRICTER PROMPT: Demanding quality for the 'Pass'
    payload = {
        "model": "gemini-3.1-flash-image-preview", 
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": "Score this handwriting 1-100. Be strict. If it is messy or very short, score below 70. Check for top-down strokes. Return JSON: {'corrected': '...', 'tips': [], 'score': 85, 'passed': true/false}"}, 
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_img}"}}
        ]}], 
        "response_format": {"type": "json_object"}
    }
    try:
        r = requests.post(f"{st.secrets['HS_BASE_URL']}/chat/completions", json=payload, headers=headers)
        return json.loads(r.json()['choices'][0]['message']['content'])
    except: return {"corrected": "Error", "tips": [], "score": 0, "passed": False}

# --- 4. MAIN UI ---
st.set_page_config(page_title="The Thinking Chest", layout="wide")
if "ghost_text" not in st.session_state: st.session_state.ghost_text = ""
if "advice" not in st.session_state: st.session_state.advice = []
if "last_score" not in st.session_state: st.session_state.last_score = 0
if "dynamic_prompt" not in st.session_state: st.session_state.dynamic_prompt = ""
if "passed" not in st.session_state: st.session_state.passed = False

curr = load_curriculum()
name = st.sidebar.radio("Identify Scribe:", ["Ollie", "Liam"])
user = get_profile(name)

# SIDEBAR HUD
st.sidebar.title(f"🏰 {user['name']}'s Vault")
st.sidebar.metric("Ink Drops", f"{user['drops']} 💧")

with st.sidebar.expander("🛠️ Toolbox"):
    tool = st.radio("Tool:", ["Pen", "Eraser"], horizontal=True)
    st.divider()
    for tier, items in INK_TIERS.items():
        st.caption(tier)
        for ink_name, hex_code in items.items():
            if hex_code in user['unlocked_inks']:
                if st.button(f"✨ {ink_name}" if user['active_ink'] == hex_code else ink_name, key=ink_name):
                    user['active_ink'] = hex_code; save_profile(user); st.rerun()

# --- 5. THE QUEST ---
st.title(f"🧙‍♂️ Level {user['week_idx'] + 1}: {curr[user['week_idx']]['skill']}")

if 'choice' not in st.session_state:
    c1, c2 = st.columns(2)
    if c1.button("🧠 LOGIC"): 
        st.session_state.choice = 'logic'
        st.session_state.dynamic_prompt = get_journal_prompt(user, curr[user['week_idx']])
        st.rerun()
    if c2.button("🎨 CREATIVE"): 
        st.session_state.choice = 'creative'
        st.session_state.dynamic_prompt = get_journal_prompt(user, curr[user['week_idx']])
        st.rerun()

if 'choice' in st.session_state:
    st.info(f"**JOURNAL ENTRY:** {st.session_state.dynamic_prompt}")
    
    # CANVAS & CSS (Simplified for briefness)
    lh = 45
    st.markdown(f"""<style>.stCanvas {{ border: 4px solid #31333F; border-radius: 10px; background-image: linear-gradient(#e1e1e1 2px, transparent 1px); background-size: 100% {lh}px; position: relative; }}
    .stCanvas::before {{ content: "{st.session_state.ghost_text.replace('"', '')}"; font-family: 'SchoolDots', monospace; font-size: {lh-8}px; color: rgba(0,0,0,0.15); position: absolute; top: 10px; left: 15px; pointer-events: none; white-space: pre-wrap; }}
    </style>""", unsafe_allow_html=True)

    canvas_result = st_canvas(stroke_width=3 if tool == "Pen" else 20, stroke_color=user['active_ink'] if tool == "Pen" else "#FFFFFF", background_color="rgba(0,0,0,0)", height=400, key=f"canv_{user['week_idx']}")

    col1, col2 = st.columns(2)
    if col1.button("🔍 Submit for Review"):
        with st.spinner("The Master Scribe is judging..."):
            res = analyze_scribe_work(canvas_result.image_data)
            st.session_state.ghost_text, st.session_state.last_score, st.session_state.passed = res['corrected'], res['score'], res.get('passed', False)
            if not st.session_state.passed: st.error(f"Score: {st.session_state.last_score}. Quality too low! Erase and try again.")
            st.rerun()

    # THE GATE: Only show Seal Chest if they passed (score > 70 usually)
    if st.session_state.passed:
        if col2.button("✨ Seal Chest & Level Up"):
            user['drops'] += 150; user['week_idx'] += 1; save_profile(user)
            st.balloons(); del st.session_state.choice; st.session_state.passed = False; st.rerun()