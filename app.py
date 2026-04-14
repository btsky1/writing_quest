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

if not os.path.exists("gallery"): os.makedirs("gallery")

# --- 2. INK CODEX ---
INK_TIERS = {
    "⚪ COMMON": {"Midnight": "#000000", "Graphite": "#4F4F4F", "Scholar Blue": "#1E90FF", "Crimson": "#8B0000", "Forest": "#228B22"},
    "🟢 MAGIC": {"Phoenix Ember": "#FF4500", "Seafoam": "#20B2AA", "Amethyst": "#9966CC", "Cobalt": "#0047AB", "Amber": "#FFBF00"},
    "🟣 RARE (GLOW)": {"Cyber Lime": "#39FF14", "Plasma Pink": "#FF007F", "Glacial Ice": "#00FFFF", "Electric Purple": "#BF00FF", "Lava": "#FF0000"},
    "🟡 LEGENDARY (HYPER)": {"SUPERNOVA": "#FFFACD", "ABYSS": "#1A1A1A", "UNICORN DUST": "#FFB6C1", "QUICKSILVER": "#C0C0C0", "SOLAR FLARE": "#FFD700"}
}

# --- 3. VISION RELAY (Unified) ---
def analyze_scribe_work(image_bytes):
    encoded_img = base64.b64encode(image_bytes).decode('utf-8')
    headers = {"Authorization": f"Bearer {st.secrets['HS_API_KEY']}", "Content-Type": "application/json"}
    payload = {
        "model": "gemini-3.1-flash-image-preview", 
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": "Score this 7yo's writing 1-100. Be strict on stroke order (top-down) and spelling. Return JSON: {'corrected': '...', 'tips': ['...', '...'], 'score': 85, 'passed': true/false}"}, 
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_img}"}}
        ]}], 
        "response_format": {"type": "json_object"}
    }
    try:
        r = requests.post(f"{st.secrets['HS_BASE_URL']}/chat/completions", json=payload, headers=headers)
        return json.loads(r.json()['choices'][0]['message']['content'])
    except: return {"corrected": "The Scribe is resting.", "tips": [], "score": 0, "passed": False}

def get_journal_prompt(skill, choice):
    headers = {"Authorization": f"Bearer {st.secrets['HS_API_KEY']}", "Content-Type": "application/json"}
    payload = {"model": "gemini-3.1-flash", "messages": [{"role": "system", "content": f"One short 7yo journal prompt. Skill: {skill}. Type: {choice}."}]}
    try:
        r = requests.post(f"{st.secrets['HS_BASE_URL']}/chat/completions", json=payload, headers=headers)
        return r.json()['choices'][0]['message']['content']
    except: return "Write a story about a brave cat."

# --- 4. MAIN UI ---
st.set_page_config(page_title="The Thinking Chest", layout="wide")

for key in ["ghost_text", "advice", "last_score", "passed", "teacher_auth", "dyn_prompt", "paper_bonus"]:
    if key not in st.session_state: st.session_state[key] = False if "auth" in key or "passed" in key or "bonus" in key else ""

curr = load_curriculum()
name = st.sidebar.radio("Identify Scribe:", ["Ollie", "Liam"])
user = get_profile(name)

# Sidebar HUD
st.sidebar.title(f"🏰 {user['name']}'s Vault")
st.sidebar.metric("Ink Drops", f"{user['drops']} 💧")

# TOOLBOX
with st.sidebar.expander("🛠️ Toolbox", expanded=True):
    tool = st.radio("Tool:", ["Pen", "Eraser"], horizontal=True)
    st.divider()
    for tier, items in INK_TIERS.items():
        st.caption(tier)
        for ink_name, hex_code in items.items():
            cost = 250 if "COMMON" in tier else 750 if "MAGIC" in tier else 1500 if "RARE" in tier else 5000
            c1, c2 = st.columns([1, 4])
            c1.markdown(f'<div style="background-color:{hex_code}; width:15px; height:15px; border-radius:3px; margin-top:8px;"></div>', unsafe_allow_html=True)
            if hex_code in user['unlocked_inks']:
                if c2.button(f"✨ {ink_name}" if user['active_ink'] == hex_code else ink_name, key=f"ink_{ink_name}"):
                    user['active_ink'] = hex_code; save_profile(user); st.rerun()
            else:
                if c2.button(f"Unlock {cost}", key=f"buy_{ink_name}"):
                    if user['drops'] >= cost:
                        user['drops'] -= cost; user['unlocked_inks'].append(hex_code); save_profile(user); st.rerun()

# PAPER PILOT
with st.sidebar.expander("📝 Paper Pilot (+10 💧 Bonus)"):
    up = st.file_uploader("Upload physical paper photo", type=["jpg", "png", "jpeg"])
    if up and st.button("Process Paper"):
        with st.spinner("Scanning..."):
            res = analyze_scribe_work(up.getvalue())
            st.session_state.ghost_text, st.session_state.passed, st.session_state.paper_bonus = res['corrected'], res.get('passed', False), True
            st.success("Paper analyzed! Now refine it on the iPad below.")

# TEACHER'S DESK
with st.sidebar.expander("🔐 Coordinator Access"):
    if not st.session_state.teacher_auth:
        if st.text_input("Passcode", type="password") == "AXIS2026": st.session_state.teacher_auth = True; st.rerun()
    else:
        if st.button("Manual Level Up"): user['week_idx'] += 1; save_profile(user); st.rerun()
        if st.button("Reset Drops"): user['drops'] = 100; save_profile(user); st.rerun()

# --- 5. THE QUEST ---
st.title(f"🧙‍♂️ Level {user['week_idx'] + 1}: {curr[user['week_idx']]['skill']}")
if not st.session_state.dyn_prompt:
    c1, c2 = st.columns(2)
    if c1.button("🧠 LOGIC"): st.session_state.choice, st.session_state.dyn_prompt = 'logic', get_journal_prompt(curr[user['week_idx']]['skill'], 'logic'); st.rerun()
    if c2.button("🎨 CREATIVE"): st.session_state.choice, st.session_state.dyn_prompt = 'creative', get_journal_prompt(curr[user['week_idx']]['skill'], 'creative'); st.rerun()

if st.session_state.dyn_prompt:
    st.info(f"**JOURNAL QUEST:** {st.session_state.dyn_prompt}")
    lh = 50 if user['xp']['precision'] < 75 else 40
    is_leg = any(user['active_ink'] in items.values() for tier, items in INK_TIERS.items() if "LEGENDARY" in tier)
    glow = f"filter: drop-shadow(0 0 10px {user['active_ink']}) drop-shadow(0 0 15px {user['active_ink']});" if is_leg else ""

    st.markdown(f"""<style>
        @font-face {{ font-family: 'SchoolDots'; src: url('https://raw.githubusercontent.com/btsky1/writing_quest/main/fonts/school_dots.ttf'); }}
        .stCanvas {{ border: 4px solid #31333F; border-radius: 10px; background-image: linear-gradient(#e1e1e1 2px, transparent 1px); background-size: 100% {lh}px; position: relative; {glow} }}
        .stCanvas::before {{ content: "{st.session_state.ghost_text.replace('"', '')}"; font-family: 'SchoolDots', monospace; font-size: {lh-8}px; color: rgba(0,0,0,0.15); position: absolute; top: 10px; left: 15px; pointer-events: none; white-space: pre-wrap; }}
    </style>""", unsafe_allow_html=True)

    canvas_result = st_canvas(stroke_width=3 if tool == "Pen" else 25, stroke_color=user['active_ink'] if tool == "Pen" else "#FFFFFF", background_color="rgba(0,0,0,0)", height=400, key=f"canv_{user['week_idx']}")

    b1, b2 = st.columns(2)
    if b1.button("🔍 Check iPad Scribing"):
        if canvas_result.image_data is not None:
            img = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA').convert("RGB")
            buf = io.BytesIO(); img.save(buf, format="JPEG")
            res = analyze_scribe_work(buf.getvalue())
            st.session_state.ghost_text, st.session_state.advice, st.session_state.last_score, st.session_state.passed = res['corrected'], res.get('tips', []), res['score'], res.get('passed', False)
            if not st.session_state.passed: st.warning("Not quite, Scribe! Erase and trace the Ghost.")
            st.rerun()

    if st.session_state.passed:
        if b2.button("✨ Seal Chest"):
            bonus = 10 if st.session_state.paper_bonus else 0
            user['drops'] += (150 + bonus); user['week_idx'] += 1; save_profile(user)
            st.toast(f"Earned 150 + {bonus} bonus drops!", icon="💧"); st.balloons()
            st.session_state.ghost_text, st.session_state.passed, st.session_state.dyn_prompt, st.session_state.paper_bonus = "", False, "", False
            st.rerun()