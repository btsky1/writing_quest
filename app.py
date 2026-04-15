import streamlit as st
import requests
import base64
import json
import os
import io
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
        "Shadow Blue": "#1B263B", 
        "Rusty Iron": "#8B4513", 
        "Forest Verge": "#2D5A27"
    },
    "Rare (1000💧)": {
        "Electric Teal": "#00CED1", 
        "Crimson Spark": "#FF4500", 
        "Midnight Luminous": "#191970"
    },
    "Magic (2500💧)": {
        "Void Shard": "#4B0082", 
        "Dragon Scale": "#FFD700", 
        "Frostbite Glow": "#A0E7E5"
    },
    "Legendary (10000💧)": {
        "Occam's Lazer": "#FF00FF", 
        "The Socratic Spark": "#FFFFFF", 
        "Euler's Ether": "#00FF7F"
    }
}

def get_profile(name):
    path = f"{name.lower()}_vault.json"
    defaults = {
        "name": name, 
        "drops": 500, 
        "xp": 0,
        "week_idx": 0, 
        "daily_count": 0, 
        "active_ink_hex": "#1B263B", 
        "active_ink_name": "Shadow Blue",
        "unlocked_inks": {"Shadow Blue": "#1B263B"}
    }
    if os.path.exists(path):
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            # Ensure schema integrity for older save files
            for k, v in defaults.items():
                if k not in data:
                    data[k] = v
            return data
        except:
            return defaults
    return defaults

def save_profile(data):
    with open(f"{data['name'].lower()}_vault.json", 'w') as f:
        json.dump(data, f, indent=4)

# --- 2. CHRONICLE (Detailed Session State Management) ---
if 'quest' not in st.session_state:
    st.session_state.quest = False
if 'ghost' not in st.session_state:
    st.session_state.ghost = ""
if 'explanation' not in st.session_state:
    st.session_state.explanation = ""
if 'passed' not in st.session_state:
    st.session_state.passed = False
if 'debug' not in st.session_state:
    st.session_state.debug = False
if 'choice' not in st.session_state:
    st.session_state.choice = "Creative Tale"
if 'active_ink_hex' not in st.session_state:
    st.session_state.active_ink_hex = "#1B263B"

# --- 3. THE HARDENED RELAY (Nginx 500 & JSON Fix) ---
def call_oracle(messages, model="gemini-3.1-pro-preview"):
    # Ensure secrets are pristine
    api_key = st.secrets["HS_API_KEY"].strip()
    base_url = st.secrets["HS_BASE_URL"].strip().rstrip('/')
    full_url = f"{base_url}/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Constructing the dictionary explicitly to ensure valid JSON serialization
    payload = {
        "model": str(model),
        "messages": messages,
        "temperature": 0.7
    }
    
    if st.session_state.debug:
        with st.expander("🛠️ Outgoing Scroll (Debug)"):
            st.write(f"Endpoint: {full_url}")
            st.json(payload) # This will show if the dictionary is valid
            
    try:
        # Use json=payload to let the requests library handle the serialization/commas
        r = requests.post(
            full_url, 
            json=payload, 
            headers=headers, 
            timeout=60
        )
        
        if r.status_code != 200:
            st.error(f"🏰 Oracle Tower Rejected Request (Error {r.status_code})")
            with st.expander("Nginx Response Details"):
                st.code(r.text)
            st.stop()
            return None
            
        return r.json()['choices'][0]['message']['content']
    except Exception as e:
        st.error(f"The scroll was lost: {str(e)}")
        return None

# --- 4. THE GREAT HALL (Full UI & Glow Engine) ---
st.set_page_config(page_title="The Thinking Chest", layout="wide")

if not LIBS_OK:
    st.error(f"Critical Library Missing: {ERR_MSG}")
    st.stop()

# Determine rarity effects for the Glow Engine
current_hex = st.session_state.active_ink_hex
is_legendary = any(current_hex == v for d in INK_CATALOG.values() for v in d.values() if "Legendary" in str(d))
glow_intensity = "25px" if is_legendary else "8px"

st.markdown(f"""
    <style>
    /* THE NOTEBOOK GRID SYSTEM */
    .stCanvas {{ 
        background-color: #1a1c23 !important;
        background-image: linear-gradient(rgba(255,255,255,0.05) 1px, transparent 1px) !important;
        background-size: 100% 45px !important;
        border: 3px solid #444; 
        border-radius: 12px;
    }}
    /* THE NEON GLOW ENGINE */
    canvas {{ 
        filter: drop-shadow(0 0 {glow_intensity} {current_hex}); 
    }} 
    .ink-swatch {{
        width: 50px; 
        height: 50px; 
        border-radius: 50%; 
        border: 2px solid white;
        display: inline-block; 
        vertical-align: middle; 
        margin-right: 15px;
        transition: transform 0.3s ease;
    }}
    .ink-swatch:hover {{
        transform: scale(1.1);
    }}
    </style>
""", unsafe_allow_html=True)

# --- 5. SIDEBAR: IDENTITY & ARMOURY ---
name = st.sidebar.radio("Identify Scribe:", ["Ollie", "Liam"])
user = get_profile(name)
track = st.sidebar.radio("Learning Track:", ["English Master", "Mandarin Scribe"])

with st.sidebar:
    st.divider()
    st.metric("Ink Drops", f"{user['drops']} 💧", f"{user['xp']} XP")
    
    st.subheader("🖋️ Scribe's Vault")
    selected_ink_name = st.selectbox("Your Unlocked Pigments", list(user['unlocked_inks'].keys()))
    user['active_ink_name'] = selected_ink_name
    user['active_ink_hex'] = user['unlocked_inks'][selected_ink_name]
    st.session_state.active_ink_hex = user['active_ink_hex']
    
    # Active Preview Swatch
    st.markdown(f'<div class="ink-swatch" style="background-color:{user["active_ink_hex"]}; box-shadow: 0 0 {glow_intensity} {user["active_ink_hex"]};"></div>', unsafe_allow_html=True)

    # THE ARMOURY SHOP (Explicit Logic)
    st.markdown("### ⚔️ The Armoury Shop")
    with st.expander("Forge New Pigments"):
        tier_label = st.selectbox("Select Tier", list(INK_CATALOG.keys()))
        
        # Explicit Pricing Matrix
        if "Common" in tier_label: price = 250
        elif "Rare" in tier_label: price = 1000
        elif "Magic" in tier_label: price = 2500
        else: price = 10000
        
        tier_inks = INK_CATALOG[tier_label]
        target_ink_name = st.selectbox("Choose Pigment", list(tier_inks.keys()))
        target_hex = tier_inks[target_ink_name]
        
        # Shop Preview
        shop_glow = "15px" if price >= 2500 else "5px"
        st.markdown(f'<div class="ink-swatch" style="background-color:{target_hex}; box-shadow: 0 0 {shop_glow} {target_hex};"></div>', unsafe_allow_html=True)
        st.write(f"**Investment Cost:** {price} 💧")
        
        if st.button(f"Forge {target_ink_name}"):
            if user['drops'] >= price:
                if target_ink_name not in user['unlocked_inks']:
                    user['drops'] -= price
                    user['unlocked_inks'][target_ink_name] = target_hex
                    save_profile(user)
                    st.success(f"Successfully forged {target_ink_name}!")
                    st.rerun()
                else:
                    st.info("You already possess this pigment.")
            else:
                st.error("Insufficient Ink Drops.")

    # TEACHER'S DESK (The Coordinator Overrides)
    with st.expander("🔐 Teacher's Desk"):
        coord_key = st.text_input("Vault Security Key", type="password")
        if coord_key == st.secrets.get("VAULT_KEY", "67"):
            st.success("Access Granted")
            if st.button("Grant 10,000💧 Reward"):
                user['drops'] += 10000
                save_profile(user)
                st.rerun()
            st.session_state.debug = st.toggle("Enable Oracle Debug Mode")
    
    if st.button("🔄 Reset Current Quest Scroll"):
        st.session_state.quest = False
        st.rerun()

# --- 6. THE QUEST GENERATOR ---
st.title(f"🏰 {track}: Level {user['week_idx'] + 1}")

if not st.session_state.quest:
    st.session_state.choice = st.radio("Choose Quest Path:", ["Creative Tale", "Logical Analysis", "Survival Skill"], horizontal=True)
    
    if st.button("🔓 Break the Seal"):
        with st.spinner("The Oracle is drawing from the Socratic Ether..."):
            prompt = (
                f"Act as a G6 Master Teacher. {user['name']} is on the {track} track. "
                f"Design a specific {st.session_state.choice} task suitable for their level. "
                "Provide the task description only. Be clear and inspiring."
            )
            res = call_oracle([{"role": "user", "content": prompt}])
            if res:
                st.session_state.quest = res
                st.rerun()

# --- 7. ACTIVE QUEST UI ---
if st.session_state.quest:
    st.info(st.session_state.quest)
    
    # 7.1 PAPER PILOT (Vision Analysis)
    with st.expander("📷 Paper Pilot (Physical Scan)"):
        cam_image = st.camera_input("Snapshot your physical notebook draft")
        if cam_image and st.button("Submit to Oracle"):
            with st.spinner("Scanning ink patterns..."):
                b64 = base64.b64encode(cam_image.getvalue()).decode('utf-8')
                v_msg = [{"role": "user", "content": [
                    {"type": "text", "text": "Analyze the writing. Return strictly JSON: 'corrected', 'explanation', 'passed' (bool)."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                ]}]
                res = call_oracle(v_msg, model="gemini-3.1-flash-image-preview")
                if res:
                    try:
                        data = json.loads(res.replace("```json", "").replace("```", "").strip())
                        st.session_state.ghost = data.get('corrected', "")
                        st.session_state.explanation = data.get('explanation', "")
                        st.rerun()
                    except:
                        st.error("Oracle Vision failed to parse JSON.")

    # 7.2 THE COUNSEL & AUDIO
    if st.session_state.explanation:
        c1, c2 = st.columns([4, 1])
        c1.success(f"📜 **Master's Counsel:** {st.session_state.explanation}")
        with c2:
            if st.button("🔊 Hear Counsel"):
                tts_lang = 'zh-CN' if track == "Mandarin Scribe" else 'en'
                tts = gTTS(text=st.session_state.explanation, lang=tts_lang)
                fp = io.BytesIO()
                tts.write_to_fp(fp)
                fp.seek(0)
                st.audio(fp, format='audio/mp3')
        
        # MANDARIN VOICE PRACTICE (Full Mic Logic)
        if track == "Mandarin Scribe":
            st.subheader("🎤 Tonal Practice")
            recorded = mic_recorder(start_prompt="Record your attempt", stop_prompt="Stop Recording", key='m_rec_v65')
            if recorded:
                st.audio(recorded['bytes'])
                st.info("Compare your tones to the Master's audio above.")

    # 7.3 THE SCRIBING CANVAS
    # Ghost text tracing (Notebook Font Style)
    ghost_opacity = 0.15 if not st.session_state.passed else 0.50
    st.markdown(f"""
        <p style="color:rgba(255,255,255,{ghost_opacity}); font-family:'Courier New', Courier, monospace; 
        font-size:32px; margin-bottom:-45px; padding-left:20px; font-weight:bold; 
        pointer-events:none; line-height:45px; white-space: pre-wrap;">
        {st.session_state.ghost}
        </p>
    """, unsafe_allow_html=True)

    canvas_key = f"v65_{track}_{user['week_idx']}_{user['daily_count']}"
    canvas_result = st_canvas(
        stroke_width=4,
        stroke_color=user['active_ink_hex'],
        background_color="rgba(0,0,0,0)",
        height=500,
        key=canvas_key
    )

    # 7.4 EVALUATION & REWARDS (XP Engine)
    col_eval, col_seal = st.columns(2)
    
    if col_eval.button("🔍 Check iPad Scribing"):
        if canvas_result.image_data is not None:
            raw_img = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA').convert("RGB")
            buffer = io.BytesIO()
            raw_img.save(buffer, format="JPEG")
            b64_canvas = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            with st.spinner("Evaluating your precision..."):
                e_msg = [{"role": "user", "content": [
                    {"type": "text", "text": "Evaluate tracing accuracy. Return JSON: 'corrected', 'explanation', 'passed'."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_canvas}"}}
                ]}]
                eval_res = call_oracle(e_msg, model="gemini-3.1-flash-image-preview")
                if eval_res:
                    try:
                        res_json = json.loads(eval_res.replace("```json", "").replace("```", "").strip())
                        st.session_state.ghost = res_json.get('corrected', "")
                        st.session_state.explanation = res_json.get('explanation', "")
                        st.session_state.passed = res_json.get('passed', False)
                        st.rerun()
                    except:
                        st.error("The Oracle's evaluation was inconclusive.")

    if st.session_state.passed:
        if col_seal.button("✨ Seal the Quest"):
            # REWARD CALCULATION (Mandarin Multiplier)
            reward = 150 * (2 if track == "Mandarin Scribe" else 1)
            user['drops'] += reward
            user['xp'] += 25
            user['daily_count'] += 1
            
            # Level Up Progression
            if user['daily_count'] >= 3:
                user['daily_count'] = 0
                user['week_idx'] += 1
                st.balloons()
            
            save_profile(user)
            # Reset Quest States
            st.session_state.quest = False
            st.session_state.passed = False
            st.session_state.ghost = ""
            st.session_state.explanation = ""
            st.rerun()