import streamlit as st
import requests, base64, json, os, io
from PIL import Image

# --- 0. LIBRARY & HARDWARE INTEGRITY ---
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
            with open(path, 'r') as f:
                data = json.load(f)
            # Ensure new schema features exist in old save files
            for k, v in defaults.items():
                if k not in data: data[k] = v
            return data
        except: return defaults
    return defaults

def save_profile(data):
    with open(f"{data['name'].lower()}_vault.json", 'w') as f:
        json.dump(data, f)

# --- 2. CHRONICLE (Session State Management) ---
if 'quest' not in st.session_state: st.session_state.quest = False
if 'ghost' not in st.session_state: st.session_state.ghost = ""
if 'explanation' not in st.session_state: st.session_state.explanation = ""
if 'passed' not in st.session_state: st.session_state.passed = False
if 'debug' not in st.session_state: st.session_state.debug = False
if 'choice' not in st.session_state: st.session_state.choice = "Creative Tale"

# --- 3. THE HARDENED RELAY (The 500 Fix) ---
def call_oracle(messages, model="gemini-3.1-pro-preview"):
    # Force clean secrets to prevent Nginx double-slash // errors
    api_key = st.secrets["HS_API_KEY"].strip()
    base_url = st.secrets["HS_BASE_URL"].strip().rstrip('/')
    full_url = f"{base_url}/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}", 
        "Content-Type": "application/json"
    }
    
    payload = {"model": model, "messages": messages}
    
    if st.session_state.debug:
        with st.expander("🛠️ Oracle Payload Debug"):
            st.write(f"Final Endpoint: {full_url}")
            st.json(payload)
            
    try:
        r = requests.post(full_url, json=payload, headers=headers, timeout=45)
        if r.status_code != 200:
            st.error(f"Oracle Connection Error ({r.status_code})")
            st.code(r.text) # Shows Nginx internal error for debugging
            st.stop()
            return None
        return r.json()['choices'][0]['message']['content']
    except Exception as e:
        st.error(f"The scroll failed to reach the tower: {str(e)}")
        return None

# --- 4. THE GREAT HALL (UI & GLOW ENGINE) ---
st.set_page_config(page_title="The Thinking Chest", layout="wide")

if not LIBS_OK:
    st.error(f"Critical Library Missing: {ERR_MSG}"); st.stop()

# Determine Glow intensity based on rarity
current_hex = st.session_state.get('active_ink_hex', '#FFFFFF')
is_legendary = any(current_hex == v for d in INK_CATALOG.values() for v in d.values() if "Legendary" in str(d))
glow_intensity = "22px" if is_legendary else "7px"

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
        width: 48px; height: 48px; border-radius: 50%; border: 2px solid white;
        display: inline-block; margin-right: 12px; vertical-align: middle;
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
    
    # COLLECTION SECTION
    st.subheader("🖋️ Current Pigment")
    selected_ink_name = st.selectbox("Your Collection", list(user['unlocked_inks'].keys()))
    user['active_ink_name'] = selected_ink_name
    user['active_ink_hex'] = user['unlocked_inks'][selected_ink_name]
    st.session_state['active_ink_hex'] = user['active_ink_hex']
    
    # Live Collection Preview
    st.markdown(f'<div class="ink-swatch" style="background-color:{user["active_ink_hex"]}; box-shadow: 0 0 {glow_intensity} {user["active_ink_hex"]};"></div>', unsafe_allow_html=True)

    # THE ARMOURY SHOP
    st.markdown("### ⚔️ The Armoury ink shop")
    with st.expander("Forge New Inks"):
        tier_label = st.selectbox("Browse Tier", list(INK_CATALOG.keys()))
        
        # Explicit Pricing logic
        if "Common" in tier_label: price = 250
        elif "Rare" in tier_label: price = 1000
        elif "Magic" in tier_label: price = 2500
        else: price = 10000 # Legendary
        
        inks_in_tier = INK_CATALOG[tier_label]
        target_ink = st.selectbox("Choose Pigment", list(inks_in_tier.keys()))
        target_hex = inks_in_tier[target_ink]
        
        # Shop Preview Swatch
        shop_glow = "12px" if price >= 2500 else "4px"
        st.markdown(f'<div class="ink-swatch" style="background-color:{target_hex}; box-shadow: 0 0 {shop_glow} {target_hex};"></div>', unsafe_allow_html=True)
        st.markdown(f"**Investment:** {price} 💧")
        
        if st.button(f"Forge {target_ink}"):
            if user['drops'] >= price:
                if target_ink not in user['unlocked_inks']:
                    user['drops'] -= price
                    user['unlocked_inks'][target_ink] = target_hex
                    save_profile(user)
                    st.success(f"Successfully forged {target_ink}!"); st.rerun()
                else: st.info("You already possess this pigment.")
            else: st.error("Insufficient Ink Drops.")

    # TEACHER'S DESK (COORDINATOR OVERRIDES)
    with st.expander("🔐 Teacher's Desk"):
        coord_key = st.text_input("Vault Key", type="password")
        if coord_key == st.secrets.get("VAULT_KEY", "67"):
            if st.button("Grant 10,000💧"):
                user['drops'] += 10000; save_profile(user); st.rerun()
            st.session_state.debug = st.toggle("Show Oracle Diagnostics")
    
    if st.button("🔄 Reset Current Quest"):
        st.session_state.quest = False; st.rerun()

# --- 6. THE QUEST LOGIC ---
st.title(f"🏰 {track}: Level {user['week_idx'] + 1}")

if not st.session_state.quest:
    st.session_state.choice = st.radio("Choose your Quest:", ["Creative Tale", "Logical Analysis", "Survival Skill"], horizontal=True)
    
    if st.button("🔓 Open the Scroll"):
        with st.spinner("The Oracle is drawing upon the ether..."):
            # ROLE BYPASS: Put instructions in a single 'user' message to avoid proxy 500 errors
            combined_prompt = (
                f"Act as a G6 Master Teacher. {user['name']} is on the {track} track. "
                f"Design a specific {st.session_state.choice} task suitable for their level. "
                "Provide the task description clearly. No introductory pleasantries."
            )
            messages = [{"role": "user", "content": combined_prompt}]
            res = call_oracle(messages)
            if res:
                st.session_state.quest = res
                st.rerun()

# --- 7. ACTIVE QUEST UI ---
if st.session_state.quest:
    st.info(st.session_state.quest)
    
    # 7.1 PAPER PILOT (Vision Analysis)
    with st.expander("📷 Paper Pilot (Camera Scan)"):
        cam_image = st.camera_input("Snapshot your physical draft")
        if cam_image and st.button("Analyze Physical Ink"):
            with st.spinner("Decoding scribbles..."):
                encoded_base64 = base64.b64encode(cam_image.getvalue()).decode('utf-8')
                vision_messages = [{"role": "user", "content": [
                    {"type": "text", "text": "Analyze writing. Return strictly JSON: 'corrected', 'explanation', 'passed' (true/false)."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_base64}"}}
                ]}]
                res_str = call_oracle(vision_messages, model="gemini-3.1-flash-image-preview")
                if res_str:
                    try:
                        clean_json = res_str.replace("```json", "").replace("```", "").strip()
                        data = json.loads(clean_json)
                        st.session_state.ghost = data.get('corrected', "")
                        st.session_state.explanation = data.get('explanation', "")
                        st.rerun()
                    except: st.error("The Oracle's vision was blurry. Try again.")

    # 7.2 THE COUNSEL & AUDIO
    if st.session_state.explanation:
        c1, c2 = st.columns([4, 1])
        c1.success(f"📜 **The Master's Counsel:** {st.session_state.explanation}")
        with c2:
            if st.button("🔊 Hear Oracle"):
                tts_lang = 'zh-CN' if track == "Mandarin Scribe" else 'en'
                tts = gTTS(text=st.session_state.explanation, lang=tts_lang)
                fp = io.BytesIO(); tts.write_to_fp(fp); fp.seek(0)
                st.audio(fp, format='audio/mp3')
        
        # MANDARIN VOICE PRACTICE
        if track == "Mandarin Scribe":
            st.subheader("🎤 Voice Practice")
            recorded_audio = mic_recorder(start_prompt="Record your attempt", stop_prompt="Stop Recording", key='m_rec_v60')
            if recorded_audio:
                st.audio(recorded_audio['bytes'])
                st.info("Listen back and compare your tones to the Oracle's guidance.")

    # 7.3 TRACING & CANVAS (The Core Writing Task)
    ghost_opacity = 0.15 if not st.session_state.passed else 0.50
    st.markdown(f'<p style="color:rgba(255,255,255,{ghost_opacity}); font-family:Courier; font-size:32px; margin-bottom:-45px; padding-left:20px; font-weight:bold; pointer-events:none; line-height:40px;">{st.session_state.ghost}</p>', unsafe_allow_html=True)

    canvas_id = f"v60_{track}_{user['week_idx']}_{user['daily_count']}"
    canvas_result = st_canvas(
        stroke_width=4, stroke_color=user['active_ink_hex'], 
        background_color="rgba(0,0,0,0)", height=500, key=canvas_id
    )

    # 7.4 EVALUATION & REWARDS
    col_eval, col_seal = st.columns(2)
    if col_eval.button("🔍 Check iPad Scribing"):
        if canvas_result.image_data is not None:
            raw_img = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA').convert("RGB")
            buffer = io.BytesIO(); raw_img.save(buffer, format="JPEG"); b64_canvas = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            with st.spinner("The Oracle evaluates your ink..."):
                eval_messages = [{"role": "user", "content": [
                    {"type": "text", "text": "Evaluate tracing accuracy. Return JSON: 'corrected', 'explanation', 'passed'."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_canvas}"}}
                ]}]
                eval_res = call_oracle(eval_messages, model="gemini-3.1-flash-image-preview")
                if eval_res:
                    try:
                        res_json = json.loads(eval_res.replace("```json", "").replace("```", "").strip())
                        st.session_state.ghost = res_json.get('corrected', "")
                        st.session_state.explanation = res_json.get('explanation', "")
                        st.session_state.passed = res_json.get('passed', False)
                        st.rerun()
                    except: st.error("Evaluation failed. The Oracle is confused.")

    if st.session_state.passed:
        if col_seal.button("✨ Seal the Chest"):
            # Reward logic (Double for Mandarin)
            reward = 150 * (2 if track == "Mandarin Scribe" else 1)
            user['drops'] += reward
            user['daily_count'] += 1
            
            # Leveling up after 3 successes
            if user['daily_count'] >= 3:
                user['daily_count'] = 0; user['week_idx'] += 1
                st.balloons()
            
            save_profile(user)
            # Reset states for next quest
            st.session_state.quest = False
            st.session_state.passed = False
            st.session_state.ghost = ""
            st.session_state.explanation = ""
            st.rerun()