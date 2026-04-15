import streamlit as st
import requests, base64, json, os, io
from PIL import Image

# --- 0. HARDWARE & LIBRARY VERIFICATION ---
try:
    from streamlit_drawable_canvas import st_canvas
    from streamlit_mic_recorder import mic_recorder
    from gtts import gTTS
    LIBS_OK = True
except ImportError as e:
    LIBS_OK = False
    MISSING_LIB = str(e)

# --- 1. THE VAULT (DATA & ECONOMY) ---
def get_profile(name):
    path = f"{name.lower()}_vault.json"
    defaults = {
        "name": name, "drops": 100, "week_idx": 0, "daily_count": 0, 
        "en_maxed": False, "story_context": "The journey begins...", 
        "active_ink": "#ffffff", "unlocked_inks": ["#ffffff", "#000000"]
    }
    if os.path.exists(path):
        data = json.load(open(path, 'r'))
        # Ensure all keys exist (Prevents 'KeyError' during economy updates)
        for k, v in defaults.items():
            if k not in data: data[k] = v
        return data
    return defaults

def save_profile(data):
    json.dump(data, open(f"{data['name'].lower()}_vault.json", 'w'))

# --- 2. THE CHRONICLE (SESSION STATE) ---
# We use explicit initialization to ensure the app never crashes on a refresh.
if 'quest' not in st.session_state: st.session_state.quest = False
if 'ghost' not in st.session_state: st.session_state.ghost = ""
if 'explanation' not in st.session_state: st.session_state.explanation = ""
if 'passed' not in st.session_state: st.session_state.passed = False
if 'choice' not in st.session_state: st.session_state.choice = "Creative Tale"

# --- 3. THE ORACLE RELAY (HOLYSHEEP API) ---
def call_oracle(payload, endpoint="chat/completions"):
    headers = {
        "Authorization": f"Bearer {st.secrets['HS_API_KEY']}", 
        "Content-Type": "application/json"
    }
    try:
        r = requests.post(f"{st.secrets['HS_BASE_URL']}/{endpoint}", json=payload, headers=headers, timeout=35)
        if r.status_code != 200:
            st.error(f"Oracle Connection Error ({r.status_code})")
            st.code(r.text) # Raw diagnostic output
            return None
        return r.json()['choices'][0]['message']['content']
    except Exception as e:
        st.error(f"The scroll is stuck: {str(e)}")
        return None

# --- 4. THE GREAT HALL (UI & STYLING) ---
st.set_page_config(page_title="The Thinking Chest", layout="wide")

if not LIBS_OK:
    st.error(f"⚠️ Missing Library: {MISSING_LIB}"); st.stop()

st.markdown(f"""
    <style>
    .stCanvas {{ 
        background-color: #1a1c23 !important;
        background-image: linear-gradient(#2d313a 1px, transparent 1px) !important;
        background-size: 100% 40px !important;
        border: 3px solid #444; border-radius: 10px;
    }}
    canvas {{ filter: drop-shadow(0 0 3px #ffffff); }} /* Moonlight Glow */
    </style>
""", unsafe_allow_html=True)

# --- 5. SIDEBAR: IDENTITY & SHOP ---
name = st.sidebar.radio("Identify Scribe:", ["Ollie", "Liam"])
user = get_profile(name)
track = st.sidebar.radio("Learning Track:", ["English Master", "Mandarin Scribe"])

with st.sidebar:
    st.divider()
    st.metric("Ink Drops", f"{user['drops']} 💧")
    
    st.subheader("🖋️ Equipped Ink")
    user['active_ink'] = st.selectbox("Dip your pen", user['unlocked_inks'])
    
    with st.expander("🛍️ The Tiered Shop"):
        tier = st.selectbox("Select Rarity", ["Common (100💧)", "Rare (500💧)", "Legendary (1000💧)"])
        price = 100 if "Common" in tier else 500 if "Rare" in tier else 1000
        new_color = st.color_picker("Preview Pigment", "#FF00FF")
        
        if st.button(f"Unlock for {price}💧"):
            if user['drops'] >= price:
                user['drops'] -= price
                if new_color not in user['unlocked_inks']: user['unlocked_inks'].append(new_color)
                save_profile(user); st.success("Pigment Unlocked!"); st.rerun()
            else: st.error("Insufficient Drops.")

    with st.expander("🔐 Coordinator Access"):
        if st.text_input("Vault Key", type="password") == "67":
            if st.button("Grant 1000💧"): 
                user['drops'] += 1000; save_profile(user); st.rerun()

# --- 6. THE SCROLL AREA ---
st.title(f"🏰 {track}: Level {user['week_idx'] + 1}")

if not st.session_state.quest:
    # --- AGENCY: Choice of Path ---
    st.session_state.choice = st.radio("Style of Study:", ["Creative Tale", "Logical Analysis", "Survival Skill"], horizontal=True)
    if st.button("🔓 Open the Scroll"):
        with st.spinner("Decoding the scroll..."):
            instr = f"Scribe: {user['name']}. Track: {track}. Style: {st.session_state.choice}. Focus: G6/HSK logic."
            payload = {"model": "gemini-3.1-pro-preview", "messages": [{"role": "system", "content": instr}]}
            res = call_oracle(payload)
            if res:
                st.session_state.quest = res
                st.rerun()

if st.session_state.quest:
    st.info(st.session_state.quest)
    
    # --- PHASE 1: PAPER PILOT ---
    with st.expander("📷 Use Paper Pilot (Camera Scan)"):
        cam = st.camera_input("Snapshot your physical draft")
        if cam and st.button("Analyze Paper Grit"):
            with st.spinner("The Oracle is examining your ink..."):
                encoded = base64.b64encode(cam.getvalue()).decode('utf-8')
                payload = {
                    "model": "gemini-3.1-flash-image-preview",
                    "messages": [{"role": "user", "content": [
                        {"type": "text", "text": "Return JSON: 'corrected' (text), 'explanation' (logic), 'passed' (bool)."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded}"}}
                    ]}], "response_format": {"type": "json_object"}
                }
                res_str = call_oracle(payload)
                if res_str:
                    res = json.loads(res_str)
                    st.session_state.ghost = res.get('corrected', "")
                    st.session_state.explanation = res.get('explanation', "")
                    st.rerun()

    # --- PHASE 2: THE COUNSEL & VOICE ---
    if st.session_state.explanation:
        c1, c2 = st.columns([4, 1])
        c1.success(f"📜 **The Master's Counsel:** {st.session_state.explanation}")
        
        with c2:
            # Oracle's Listening Practice (Shadowing)
            if st.button("🔊 Hear Oracle"):
                tts = gTTS(text=st.session_state.explanation, lang='zh-CN' if track == "Mandarin Scribe" else 'en')
                fp = io.BytesIO(); tts.write_to_fp(fp); fp.seek(0)
                st.audio(fp, format='audio/mp3')

        # Mandarin Speaking Hurdle (Voice Input)
        if track == "Mandarin Scribe":
            st.subheader("🎤 Voice Practice")
            audio = mic_recorder(start_prompt="Record your attempt", stop_prompt="Stop", key='recorder')
            if audio:
                st.audio(audio['bytes'])
                st.info("Listen back and compare your tones to the Oracle above.")

    # --- PHASE 3: TRACING (GHOST TEXT) ---
    opac = 0.15 if not st.session_state.passed else 0.45
    st.markdown(f'<p style="color:rgba(255,255,255,{opac}); font-family:Courier; font-size:30px; margin-bottom:-45px; padding-left:20px; font-weight:bold; pointer-events:none; line-height: 40px;">{st.session_state.ghost}</p>', unsafe_allow_html=True)

    canvas_key = f"v52_{track}_{user['week_idx']}_{user['daily_count']}"
    canvas_result = st_canvas(
        stroke_width=4, stroke_color=user['active_ink'], 
        background_color="rgba(0,0,0,0)", height=500, key=canvas_key
    )

    colA, colB = st.columns(2)
    if colA.button("🔍 Check iPad Scribing"):
        if canvas_result.image_data is not None:
            img = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA').convert("RGB")
            buf = io.BytesIO(); img.save(buf, format="JPEG")
            encoded = base64.b64encode(buf.getvalue()).decode('utf-8')
            with st.spinner("Evaluating precision..."):
                payload = {
                    "model": "gemini-3.1-flash-image-preview",
                    "messages": [{"role": "user", "content": [
                        {"type": "text", "text": "Evaluate tracing. Return JSON: 'corrected', 'explanation', 'passed'."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded}"}}
                    ]}], "response_format": {"type": "json_object"}
                }
                res_str = call_oracle(payload)
                if res_str:
                    res = json.loads(res_str)
                    st.session_state.ghost, st.session_state.explanation, st.session_state.passed = res.get('corrected', ""), res.get('explanation', ""), res.get('passed', False)
                    st.rerun()

    # --- PHASE 4: REWARDS & PROGRESSION ---
    if st.session_state.passed:
        if colB.button("✨ Seal the Chest"):
            user['drops'] += 150 * (2 if track == "Mandarin Scribe" else 1)
            user['daily_count'] += 1
            if user['daily_count'] >= 3:
                user['daily_count'] = 0; user['week_idx'] += 1; st.balloons()
            save_profile(user)
            # HARD RESET: Clears the scroll for the next journey
            st.session_state.quest = False
            st.session_state.passed = False
            st.session_state.ghost = ""
            st.session_state.explanation = ""
            st.rerun()