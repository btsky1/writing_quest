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
    ERR_MSG = str(e)

# --- 1. THE ARMOURY REGISTRY (Data & Economy) ---
INK_CATALOG = {
    "Common (250💧)": {
        "Shadow Blue": "#1B263B", "Rusty Iron": "#8B4513", "Forest Verge": "#2D5A27"
    },
    "Rare (1000💧)": {
        "Electric Teal": "#00CED1", "Crimson Spark": "#FF4500", "Midnight Luminous": "#191970"
    },
    "Magic (2500💧)": {
        "Void Shard": "#4B0082", "Dragon Scale": "#FFD700", "Frostbite Glow": "#A0E7E5"
    },
    "Legendary (10000💧)": {
        "Occam's Lazer": "#FF00FF", "The Socratic Spark": "#FFFFFF", "Euler's Ether": "#00FF7F"
    }
}

def get_profile(name):
    path = f"{name.lower()}_vault.json"
    defaults = {
        "name": name, "drops": 500, "week_idx": 0, "daily_count": 0, 
        "active_ink_hex": "#1B263B", "active_ink_name": "Shadow Blue",
        "unlocked_inks": {"Shadow Blue": "#1B263B"}, "story_context": "The journey begins..."
    }
    if os.path.exists(path):
        try:
            data = json.load(open(path, 'r'))
            # Healing: Ensure old saves get new features (like hex storage)
            for k, v in defaults.items():
                if k not in data: data[k] = v
            return data
        except: return defaults
    return defaults

def save_profile(data):
    with open(f"{data['name'].lower()}_vault.json", 'w') as f:
        json.dump(data, f)

# --- 2. THE CHRONICLE (Session State) ---
# We use explicit initialization to ensure the app never crashes on state-miss
if 'quest' not in st.session_state: st.session_state.quest = False
if 'ghost' not in st.session_state: st.session_state.ghost = ""
if 'explanation' not in st.session_state: st.session_state.explanation = ""
if 'passed' not in st.session_state: st.session_state.passed = False
if 'debug' not in st.session_state: st.session_state.debug = False

# --- 3. HARDENED API RELAY (500 Error Protection) ---
def call_oracle(payload):
    headers = {
        "Authorization": f"Bearer {st.secrets['HS_API_KEY']}", 
        "Content-Type": "application/json"
    }
    if st.session_state.debug:
        with st.expander("🛠️ Oracle Payload Debug"):
            st.json(payload)
            
    try:
        # Standardizing URL to prevent gateway routing errors
        url = f"{st.secrets['HS_BASE_URL'].rstrip('/')}/chat/completions"
        r = requests.post(url, json=payload, headers=headers, timeout=45)
        
        if r.status_code != 200:
            st.error(f"Oracle Connection Error ({r.status_code})")
            st.code(r.text)
            st.stop() # Prevents infinite 'writing' spinner
            return None
        return r.json()['choices'][0]['message']['content']
    except Exception as e:
        st.error(f"The scroll failed to reach the tower: {str(e)}")
        return None

# --- 4. THE GREAT HALL (UI & GLOW ENGINE) ---
st.set_page_config(page_title="The Thinking Chest", layout="wide")

if not LIBS_OK:
    st.error(f"Critical Library Missing: {ERR_MSG}"); st.stop()

# Dynamic Glow Logic
current_hex = st.session_state.get('active_ink_hex', '#FFFFFF')
is_legendary = any(current_hex == v for d in INK_CATALOG.values() for v in d.values() if "Legendary" in str(d))
glow_intensity = "15px" if is_legendary else "6px"

st.markdown(f"""
    <style>
    .stCanvas {{ 
        background-color: #1a1c23 !important;
        background-image: linear-gradient(#2d313a 1px, transparent 1px) !important;
        background-size: 100% 40px !important;
        border: 3px solid #444; border-radius: 12px;
    }}
    canvas {{ filter: drop-shadow(0 0 {glow_intensity} {current_hex}); }} 
    .ink-swatch {{
        width: 45px; height: 45px; border-radius: 50%; border: 2px solid white;
        display: inline-block; margin-right: 10px;
    }}
    </style>
""", unsafe_allow_html=True)

# --- 5. SIDEBAR: IDENTITY & THE ARMOURY ---
name = st.sidebar.radio("Identify Scribe:", ["Ollie", "Liam"])
user = get_profile(name)
track = st.sidebar.radio("Learning Track:", ["English Master", "Mandarin Scribe"])

with st.sidebar:
    st.divider()
    st.metric("Ink Drops", f"{user['drops']} 💧")
    
    # COLLECTION MANAGEMENT
    st.subheader("🖋️ Collection")
    selected_ink = st.selectbox("Current Pigment", list(user['unlocked_inks'].keys()))
    user['active_ink_name'] = selected_ink
    user['active_ink_hex'] = user['unlocked_inks'][selected_ink]
    st.session_state['active_ink_hex'] = user['active_ink_hex']
    
    # Collection Preview
    st.markdown(f'<div class="ink-swatch" style="background-color:{user["active_ink_hex"]}; box-shadow: 0 0 {glow_intensity} {user["active_ink_hex"]};"></div>', unsafe_allow_html=True)

    # THE ARMOURY SHOP
    st.markdown("### ⚔️ The Armoury ink shop")
    with st.expander("Forge New Inks"):
        tier = st.selectbox("Browse Tier", list(INK_CATALOG.keys()))
        price = 250 if "Common" in tier else 1000 if "Rare" in tier else 2500 if "Magic" in tier else 10000
        
        choices = INK_CATALOG[tier]
        target = st.selectbox("Choose Pigment", list(choices.keys()))
        hex_val = choices[target]
        
        # Shop Preview
        s_glow = "10px" if price >= 2500 else "4px"
        st.markdown(f'<div class="ink-swatch" style="background-color:{hex_val}; box-shadow: 0 0 {s_glow} {hex_val};"></div>', unsafe_allow_html=True)
        st.markdown(f"**Investment:** {price} 💧")
        
        if st.button(f"Forge {target}"):
            if user['drops'] >= price:
                if target not in user['unlocked_inks']:
                    user['drops'] -= price
                    user['unlocked_inks'][target] = hex_val
                    save_profile(user); st.success("Forged!"); st.rerun()
                else: st.info("Owned.")
            else: st.error("Insufficient drops.")

    # COORDINATOR / TEACHER'S DESK
    with st.expander("🔐 Teacher's Desk"):
        if st.text_input("Vault Key", type="password") == "67":
            if st.button("Grant 10,000💧"):
                user['drops'] += 10000; save_profile(user); st.rerun()
            st.session_state.debug = st.toggle("Oracle Diagnostics")
    
    if st.button("🔄 Clear Stuck Scroll"):
        st.session_state.quest = False; st.rerun()

# --- 6. THE QUEST ---
st.title(f"🏰 {track}: Level {user['week_idx'] + 1}")

if not st.session_state.quest:
    st.session_state.choice = st.radio("Choose your Quest:", ["Creative Tale", "Logical Analysis", "Survival Skill"], horizontal=True)
    if st.button("🔓 Open the Scroll"):
        with st.spinner("The Oracle is preparing the scroll..."):
            # Using 'user' role for prompt to bypass Nginx 500 issues
            prompt = f"System: G6 Teacher. Task: Create a {st.session_state.choice} for {track}. Format: Direct prompt only."
            payload = {
                "model": "gemini-3.1-pro-preview", 
                "messages": [{"role": "user", "content": prompt}]
            }
            res = call_oracle(payload)
            if res:
                st.session_state.quest = res; st.rerun()

# --- 7. ACTIVE QUEST UI ---
if st.session_state.quest:
    st.info(st.session_state.quest)
    
    # 7.1 PAPER PILOT (Physical Upload)
    with st.expander("📷 Paper Pilot (Camera Scan)"):
        cam = st.camera_input("Snapshot your draft")
        if cam and st.button("Extract Ink"):
            with st.spinner("Decoding..."):
                encoded = base64.b64encode(cam.getvalue()).decode('utf-8')
                payload = {
                    "model": "gemini-3.1-flash-image-preview",
                    "messages": [{"role": "user", "content": [
                        {"type": "text", "text": "Return JSON: 'corrected', 'explanation', 'passed'."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded}"}}
                    ]}]
                }
                res_str = call_oracle(payload)
                if res_str:
                    try:
                        data = json.loads(res_str.replace("```json", "").replace("```", "").strip())
                        st.session_state.ghost, st.session_state.explanation = data.get('corrected', ""), data.get('explanation', "")
                        st.rerun()
                    except: st.error("Parsing error.")

    # 7.2 COUNSEL & AUDIO
    if st.session_state.explanation:
        c1, c2 = st.columns([4, 1])
        c1.success(f"📜 **Counsel:** {st.session_state.explanation}")
        with c2:
            if st.button("🔊 Hear Oracle"):
                tts = gTTS(text=st.session_state.explanation, lang='zh-CN' if track == "Mandarin Scribe" else 'en')
                fp = io.BytesIO(); tts.write_to_fp(fp); fp.seek(0); st.audio(fp, format='audio/mp3')
        
        # RESTORED: Mandarin Voice Practice Section
        if track == "Mandarin Scribe":
            st.subheader("🎤 Voice Practice")
            audio = mic_recorder(start_prompt="Record your attempt", stop_prompt="Stop Recording", key='m_rec')
            if audio:
                st.audio(audio['bytes'])
                st.info("Compare your tones to the Oracle's audio above.")

    # 7.3 TRACING & CANVAS
    opac = 0.15 if not st.session_state.passed else 0.45
    st.markdown(f'<p style="color:rgba(255,255,255,{opac}); font-family:Courier; font-size:32px; margin-bottom:-45px; padding-left:20px; font-weight:bold; pointer-events:none; line-height:40px;">{st.session_state.ghost}</p>', unsafe_allow_html=True)

    c_key = f"v56_{track}_{user['week_idx']}_{user['daily_count']}"
    canvas_res = st_canvas(
        stroke_width=4, stroke_color=user['active_ink_hex'], 
        background_color="rgba(0,0,0,0)", height=500, key=c_key
    )

    # 7.4 EVALUATION & REWARDS
    colA, colB = st.columns(2)
    if colA.button("🔍 Check iPad Scribing"):
        if canvas_res.image_data is not None:
            img = Image.fromarray(canvas_res.image_data.astype('uint8'), 'RGBA').convert("RGB")
            buf = io.BytesIO(); img.save(buf, format="JPEG"); encoded = base64.b64encode(buf.getvalue()).decode('utf-8')
            with st.spinner("Calculating..."):
                payload = {
                    "model": "gemini-3.1-flash-image-preview",
                    "messages": [{"role": "user", "content": [
                        {"type": "text", "text": "Evaluate. Return JSON: 'corrected', 'explanation', 'passed'."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded}"}}
                    ]}]
                }
                res_str = call_oracle(payload)
                if res_str:
                    try:
                        data = json.loads(res_str.replace("```json", "").replace("```", "").strip())
                        st.session_state.ghost, st.session_state.explanation, st.session_state.passed = data.get('corrected', ""), data.get('explanation', ""), data.get('passed', False)
                        st.rerun()
                    except: st.error("JSON Error.")

    if st.session_state.passed:
        if colB.button("✨ Seal the Chest"):
            user['drops'] += 150 * (2 if track == "Mandarin Scribe" else 1)
            user['daily_count'] += 1
            if user['daily_count'] >= 3: 
                user['daily_count'] = 0; user['week_idx'] += 1; st.balloons()
            save_profile(user)
            # Full Reset for next Quest
            for k in ['quest', 'passed', 'ghost', 'explanation']: 
                st.session_state[k] = False if k in ['quest', 'passed'] else ""
            st.rerun()