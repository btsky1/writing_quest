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
    return {
        "name": name, "drops": 100, "week_idx": 0, "daily_count": 0,
        "story_context": "A mysterious ink bottle was found...", "active_ink": "#000000",
        "xp": {"precision": 50, "logic": 50, "grit": 50}, "unlocked_inks": ["#000000"]
    }

def save_profile(data):
    with open(f"{data['name'].lower()}_vault.json", 'w') as f: json.dump(data, f)

if not os.path.exists("gallery"): os.makedirs("gallery")

# --- 2. INK CODEX ---
INK_TIERS = {
    "⚪ COMMON": {"Midnight": "#000000", "Graphite": "#4F4F4F", "Scholar Blue": "#1E90FF"},
    "🟢 MAGIC": {"Phoenix Ember": "#FF4500", "Seafoam": "#20B2AA", "Amethyst": "#9966CC"},
    "🟣 RARE (GLOW)": {"Cyber Lime": "#39FF14", "Plasma Pink": "#FF007F", "Electric Purple": "#BF00FF"},
    "🟡 LEGENDARY (HYPER)": {"SUPERNOVA": "#FFFACD", "ABYSS": "#1A1A1A", "SOLAR FLARE": "#FFD700"}
}

# --- 3. VISION RELAY (The Growth Ramp Logic) ---
def analyze_scribe_work(image_bytes, user_level):
    encoded_img = base64.b64encode(image_bytes).decode('utf-8')
    headers = {"Authorization": f"Bearer {st.secrets['HS_API_KEY']}", "Content-Type": "application/json"}
    
    # The Rubric evolves based on user_level (week_idx)
    rubric = "Basic legibility and spelling" if user_level < 5 else "Sentence variety and G4 vocabulary" if user_level < 15 else "Complex logic, G6 vocabulary, and thematic depth"
    
    payload = {
        "model": "gemini-3.1-flash-image-preview", 
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": f"""
            Analyze writing for a gifted student (Level {user_level}). 
            CURRENT RUBRIC: {rubric}.
            
            STRICT TASKS:
            1. VOCAB UPGRADE: Find a weak word. Suggest a 'Loot Tier' upgrade (RARE/LEGENDARY).
            2. COGNITIVE CHECK: If the logic is G6 level, add 10 to score.
            3. PENALTY: Flag 'sabotage' (scribbles) or 'low_effort' (single words).
            4. GROWTH: If handwriting is messy or logic is lazy for their level, 'passed' must be false.
            
            Return JSON: {{'corrected': '...', 'vocab_upgrade': {{'original': '...', 'suggestion': '...', 'tier': '...'}}, 'penalty': false, 'reason': '', 'score': 85, 'passed': true}}
            """}, 
            {"type": "image_url", "image_url": {{ "url": f"data:image/jpeg;base64,{encoded_img}" }} }
        ]}], 
        "response_format": {"type": "json_object"}
    }
    try:
        r = requests.post(f"{st.secrets['HS_BASE_URL']}/chat/completions", json=payload, headers=headers)
        return json.loads(r.json()['choices'][0]['message']['content'])
    except: return {"corrected": "The Scribe is resting.", "penalty": False, "passed": False}

def get_narrative_prompt(user):
    headers = {"Authorization": f"Bearer {st.secrets['HS_API_KEY']}", "Content-Type": "application/json"}
    payload = {
        "model": "gemini-3.1-flash", 
        "messages": [{"role": "system", "content": f"Context: {user['story_context']}. Skill: Level {user['week_idx']}. Create a G5-6 level prompt that challenges the student's logic but stays fun."}]
    }
    try:
        r = requests.post(f"{st.secrets['HS_BASE_URL']}/chat/completions", json=payload, headers=headers)
        return r.json()['choices'][0]['message']['content']
    except: return "The story continues..."

# --- 4. MAIN UI ---
st.set_page_config(page_title="The Thinking Chest", layout="wide")

for key in ["ghost_text", "upgrade_data", "passed", "teacher_auth", "dyn_prompt", "paper_bonus"]:
    if key not in st.session_state: st.session_state[key] = False if "auth" in key or "passed" in key or "bonus" in key else ""

curr = load_curriculum()
name = st.sidebar.radio("Identify Scribe:", ["Ollie", "Liam"])
user = get_profile(name)

# Sidebar HUD
st.sidebar.title(f"🏰 {user['name']}'s Vault")
st.sidebar.metric("Ink Drops", f"{user['drops']} 💧")
st.sidebar.progress(min(1.0, user['daily_count'] / 3), text=f"Daily Quests: {user['daily_count']}/3")

# TOOLBOX
with st.sidebar.expander("🛠️ Toolbox", expanded=True):
    tool = st.radio("Tool:", ["Pen", "Eraser"], horizontal=True)
    for tier, items in INK_TIERS.items():
        st.caption(tier)
        cols = st.columns(3)
        for i, (ink_name, hex_code) in enumerate(items.items()):
            if hex_code in user['unlocked_inks']:
                if cols[i%3].button(f"✨" if user['active_ink'] == hex_code else "🖋️", key=f"ink_{ink_name}", help=ink_name):
                    user['active_ink'] = hex_code; save_profile(user); st.rerun()

# PAPER PILOT
with st.sidebar.expander("📝 Paper Pilot (+10 💧 Bonus)"):
    up = st.file_uploader("Upload Paper Origin", type=["jpg", "png", "jpeg"])
    if up and st.button("Process Paper"):
        with st.spinner("Analyzing Physical Scribing..."):
            res = analyze_scribe_work(up.getvalue(), user['week_idx'])
            st.session_state.ghost_text = res['corrected']
            st.session_state.upgrade_data = res.get('vocab_upgrade')
            st.session_state.paper_bonus = True
            st.success("Paper analyzed. Now refine and upgrade on the iPad!")

# COORDINATOR ACCESS
with st.sidebar.expander("🔐 Coordinator Access"):
    if not st.session_state.teacher_auth:
        if st.text_input("Passcode", type="password") == "67": st.session_state.teacher_auth = True; st.rerun()
    else:
        if st.button("Force Level Up"): user['week_idx'] += 1; save_profile(user); st.rerun()
        if st.button("Reset Daily"): user['daily_count'] = 0; save_profile(user); st.rerun()

# --- 5. THE QUEST ---
st.title(f"🧙‍♂️ Level {user['week_idx'] + 1}")

if not st.session_state.dyn_prompt:
    if st.button("📜 Reveal Next Chapter"):
        st.session_state.dyn_prompt = get_narrative_prompt(user)
        st.rerun()

if st.session_state.dyn_prompt:
    st.info(f"**THE STORY SO FAR:** {user['story_context']}")
    st.markdown(f"### 🖋️ **Your Task:** {st.session_state.dyn_prompt}")

    if st.session_state.upgrade_data:
        u = st.session_state.upgrade_data
        st.warning(f"💎 **VOCAB UPGRADE ({u['tier']}):** Turn '{u['original']}' into **'{u['suggestion']}'** to multiply your rewards!")

    # DYNAMIC GHOST OPACITY (Fades as XP grows)
    ghost_opacity = max(0.01, 0.18 - (user['xp']['precision'] / 500))
    st.markdown(f"""<style>
        .stCanvas {{ border: 4px solid #333; border-radius: 12px; background-image: linear-gradient(#eee 1.5px, transparent 1.5px); background-size: 100% 50px; position: relative; }}
        .stCanvas::before {{ content: "{st.session_state.ghost_text.replace('"', '')}"; font-family: 'SchoolDots', monospace; font-size: 42px; color: rgba(0,0,0,{ghost_opacity}); position: absolute; top: 10px; left: 15px; pointer-events: none; white-space: pre-wrap; }}
    </style>""", unsafe_allow_html=True)

    canvas_result = st_canvas(stroke_width=3 if tool == "Pen" else 25, stroke_color=user['active_ink'] if tool == "Pen" else "#FFFFFF", background_color="rgba(0,0,0,0)", height=400, key=f"v27_canv_{user['week_idx']}")

    c1, c2 = st.columns(2)
    if c1.button("🔍 Check Refinement"):
        if canvas_result.image_data is not None:
            img = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA').convert("RGB")
            buf = io.BytesIO(); img.save(buf, format="JPEG")
            res = analyze_scribe_work(buf.getvalue(), user['week_idx'])
            
            if res.get('penalty'):
                tax = 40 if res['reason'] == 'sabotage' else 15
                user['drops'] = max(0, user['drops'] - tax); save_profile(user)
                st.error(f"⚠️ SCRIBE TAX: -{tax} Drops for {res['reason']}!"); st.rerun()
            else:
                st.session_state.ghost_text, st.session_state.passed = res['corrected'], res.get('passed', False)
                st.session_state.upgrade_data = res.get('vocab_upgrade')
                if not st.session_state.passed: st.warning(f"Score: {res['score']}. The Scribe demands higher quality for Level {user['week_idx']+1}.")
                st.rerun()

    if st.session_state.passed:
        label = "🏆 Finish Daily Archive" if user['daily_count'] >= 2 else "✨ Seal Chest"
        if c2.button(label):
            # 1.5x Multiplier if they actually used the suggested word
            mult = 1.5 if st.session_state.upgrade_data and st.session_state.upgrade_data['suggestion'].lower() in st.session_state.ghost_text.lower() else 1.0
            user['drops'] += int((150 + (10 if st.session_state.paper_bonus else 0)) * mult)
            user['daily_count'] += 1
            user['story_context'] = st.session_state.ghost_text # Keep the narrative moving
            
            if user['daily_count'] >= 3:
                user['daily_count'] = 0; user['week_idx'] += 1
                st.balloons()
            
            save_profile(user)
            # Reset state for next loop
            for k in ["ghost_text", "passed", "dyn_prompt", "paper_bonus", "upgrade_data"]: st.session_state[k] = False if "passed" in k or "bonus" in k else ""
            st.rerun()