import streamlit as st
import requests, base64, json, os, io
from PIL import Image

# --- 0. DEPLOYMENT SAFETY NET ---
try:
    from streamlit_drawable_canvas import st_canvas
    from streamlit_mic_recorder import mic_recorder
    from gtts import gTTS
    LIBS_OK = True
except ImportError as e:
    LIBS_OK = False
    MISSING_LIB = str(e)

# --- 1. DATA & FULL ECONOMY ENGINE ---
def get_profile(name):
    path = f"{name.lower()}_vault.json"
    defaults = {
        "name": name, "drops": 100, "week_idx": 0, "daily_count": 0, 
        "en_maxed": False, "story_context": "The journey begins...", 
        "active_ink": "#ffffff", "unlocked_inks": ["#ffffff", "#000000"]
    }
    if os.path.exists(path):
        data = json.load(open(path, 'r'))
        # Heal missing keys gracefully
        for k, v in defaults.items():
            if k not in data: data[k] = v
        return data
    return defaults

def save_profile(data):
    json.dump(data, open(f"{data['name'].lower()}_vault.json", 'w'))

# --- 2. SESSION STATE MANAGEMENT ---
# This prevents the "KeyError" crashes on startup
state_keys = {'quest': False, 'ghost': "", 'explanation': "", 'passed': False, 'choice': "Creative Tale"}
for key, val in state_keys.items():
    if key not in st.session_state:
        st.session_state[key] = val

# --- 3. HARDENED API RELAY ---
def call_oracle(payload, endpoint="chat/completions"):
    headers = {"Authorization": f"Bearer {st.secrets['HS_API_KEY']}", "Content-Type": "application/json"}
    try:
        r = requests.post(f"{st.secrets['HS_BASE_URL']}/{endpoint}", json=payload, headers=headers, timeout=30)
        if r.status_code != 200:
            st.error(f"The connection flickered (Status {r.status_code}). Please try again.")
            return None
        return r.json()['choices'][0]['message']['content']
    except Exception as e:
        st.error(f"The scroll is stuck. Check connection: {str(e)}")
        return None

# --- 4. UI CONFIG & STYLING ---
st.set_page_config(page_title="The Thinking Chest", layout="wide")

if not LIBS_OK:
    st.error("⚠️ Library Error. The Chest cannot open.")
    st.code(f"Missing: {MISSING_LIB}\nCheck requirements.txt on GitHub.")
    st.stop()

st.markdown(f"""
    <style>
    /* Lined Notebook & Dark Mode */
    .stCanvas {{ 
        background-color: #1a1c23 !important;
        background-image: linear-gradient(#2d313a 1px, transparent 1px) !important;
        background-size: 100% 40px !important;
        border: 3px solid #444; border-radius: 10px;
    }}
    /* Moonlight Glow for Ink */
    canvas {{ filter: drop-shadow(0 0 2px #ffffff); }} 
    </style>
""", unsafe_allow_html=True)

# --- 5. SIDEBAR: IDENTITY & ECONOMY ---
name = st.sidebar.radio("Identify Scribe:", ["Ollie", "Liam"])
user = get_profile(name)
track = st.sidebar.radio("Select Track:", ["English Master", "Mandarin Scribe"])

with st.sidebar:
    st.divider()
    st.metric("Ink Drops", f"{user['drops']} 💧")
    
    st.subheader("🖋️ Your Equipment")
    user['active_ink'] = st.selectbox("Equip Ink", user['unlocked_inks'])
    
    with st.expander("🛍️ The Ink Shop"):
        tier = st.selectbox("Select Rarity", ["Common (100💧)", "Rare (500💧)", "Legendary (1000💧)"])
        price = 100 if "Common" in tier else 500 if "Rare" in tier else 1000
        new_color = st.color_picker("Discover Pigment", "#FFD700")
        
        if st.button(f"Purchase for {price}💧"):
            if user['drops'] >= price:
                user['drops'] -= price
                if new_color not in user['unlocked_inks']:
                    user['unlocked_inks'].append(new_color)
                save_profile(user)
                st.success("Pigment Unlocked!"); st.rerun()
            else: 
                st.error("Not enough drops.")

    with st.expander("🔐 Coordinator Panel"):
        if st.text_input("Access Code", type="password") == "67":
            if st.button("Grant 1000 Drops"): 
                user['drops'] += 1000; save_profile(user); st.rerun()

# --- 6. THE QUEST AREA ---
st.title(f"🏰 {track}: Level {user['week_idx'] + 1}")

# Phase 1: Student Agency
if not st.session_state.quest:
    st.session_state.choice = st.radio("Choose your approach:", ["Creative Tale", "Logical Analysis", "Survival Skill"], horizontal=True)
    if st.button("🔓 Open the Scroll"):
        with st.spinner("The Oracle is preparing your challenge..."):
            instr = f"Context: {user['story_context']}. Track: {track}. Style: {st.session_state.choice}. Task: Provide a short, engaging prompt."
            payload = {"model": "gemini-3.1-flash", "messages": [{"role": "system", "content": instr}]}
            res = call_oracle(payload)
            if res:
                st.session_state.quest = res
                st.rerun()

# Phase 2: Active Quest
if st.session_state.quest:
    # Always show the prompt at the top
    st.info(st.session_state.quest)
    
    # Paper Pilot (Drafting Phase)
    with st.expander("📷 Use Paper Pilot (Camera Scan)"):
        cam = st.camera_input("Snapshot your physical draft")
        if cam and st.button("Analyze Paper"):
            with st.spinner("Decoding your grit..."):
                encoded = base64.b64encode(cam.getvalue()).decode('utf-8')
                payload = {
                    "model": "gemini-3.1-flash-image-preview",
                    "messages": [{"role": "user", "content": [
                        {"type": "text", "text": f"Scribe: {user['name']}. Track: {track}. Return JSON: 'corrected' (perfect version), 'explanation' (G6 level logic), 'passed' (bool)."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded}"}}
                    ]}], "response_format": {"type": "json_object"}
                }
                res_str = call_oracle(payload)
                if res_str:
                    try:
                        res = json.loads(res_str)
                        st.session_state.ghost = res.get('corrected', "")
                        st.session_state.explanation = res.get('explanation', "")
                        st.success("Draft injected. Read the Counsel below.")
                    except json.JSONDecodeError:
                        st.error("The Oracle's response was garbled. Please try again.")

    # Feedback & Audio Support
    if st.session_state.explanation:
        c1, c2 = st.columns([4, 1])
        c1.success(f"📜 **The Master's Counsel:** {st.session_state.explanation}")
        with c2:
            if st.button("🔊 Hear Oracle"):
                tts = gTTS(text=st.session_state.explanation, lang='zh-CN' if track == "Mandarin Scribe" else 'en')
                fp = io.BytesIO(); tts.write_to_fp(fp); fp.seek(0)
                st.audio(fp, format='audio/mp3')

    # The Tracing Canvas
    opac = 0.15 if not st.session_state.passed else 0.45
    st.markdown(f'<p style="color:rgba(255,255,255,{opac}); font-family:Courier; font-size:32px; margin-bottom:-45px; padding-left:20px; font-weight:bold; pointer-events:none; line-height: 40px;">{st.session_state.ghost}</p>', unsafe_allow_html=True)

    # Dynamic key forces canvas to reset properly on new quests
    canvas_key = f"v5_{track}_{user['week_idx']}_{user['daily_count']}"
    canvas_result = st_canvas(
        stroke_width=4, 
        stroke_color=user['active_ink'], 
        background_color="rgba(0,0,0,0)", 
        height=500, 
        key=canvas_key,
        drawing_mode="freedraw"
    )

    # Precision Verification
    colA, colB = st.columns(2)
    if colA.button("🔍 Check iPad Scribing"):
        if canvas_result.image_data is not None:
            img = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA').convert("RGB")
            buf = io.BytesIO(); img.save(buf, format="JPEG")
            encoded = base64.b64encode(buf.getvalue()).decode('utf-8')
            
            with st.spinner("Weighing logic and strokes..."):
                payload = {
                    "model": "gemini-3.1-flash-image-preview",
                    "messages": [{"role": "user", "content": [
                        {"type": "text", "text": f"Evaluate tracing for {user['name']}. Track: {track}. Return strict JSON: 'corrected', 'explanation', 'passed'."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded}"}}
                    ]}], "response_format": {"type": "json_object"}
                }
                res_str = call_oracle(payload)
                if res_str:
                    try:
                        res = json.loads(res_str)
                        st.session_state.ghost = res.get('corrected', "")
                        st.session_state.explanation = res.get('explanation', "")
                        st.session_state.passed = res.get('passed', False)
                        if not st.session_state.passed:
                            st.warning("Precision check failed. Refine your strokes.")
                    except json.JSONDecodeError:
                        st.error("Evaluation failed to parse.")
            st.rerun()

    # The Reward Cycle
    if st.session_state.passed:
        if colB.button("✨ Seal the Chest"):
            user['drops'] += 150 * (2 if track == "Mandarin Scribe" else 1)
            user['daily_count'] += 1
            if user['daily_count'] >= 3:
                user['daily_count'] = 0; user['week_idx'] += 1; st.balloons()
            save_profile(user)
            # Reset states for the next loop
            for k in ['quest', 'ghost', 'explanation', 'passed']: 
                st.session_state[k] = False if k in ['quest', 'passed'] else ""
            st.rerun()