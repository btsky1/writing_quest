import streamlit as st
import requests, base64, json, os, io
from PIL import Image

# --- 0. LIBRARY CHECK ---
try:
    from streamlit_drawable_canvas import st_canvas
    from streamlit_mic_recorder import mic_recorder
    from gtts import gTTS
    LIBS_OK = True
except ImportError as e:
    LIBS_OK = False
    ERR = str(e)

# --- 1. THE ARMOURY DATA (ECONOMY & VAULT) ---
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
        "active_ink_name": "Shadow Blue", "active_ink_hex": "#1B263B",
        "unlocked_inks": {"Shadow Blue": "#1B263B"}, "story_context": "The journey begins..."
    }
    if os.path.exists(path):
        data = json.load(open(path, 'r'))
        for k, v in defaults.items():
            if k not in data: data[k] = v
        return data
    return defaults

def save_profile(data):
    json.dump(data, open(f"{data['name'].lower()}_vault.json", 'w'))

# --- 2. SESSION STATE ---
if 'quest' not in st.session_state: st.session_state.quest = False
if 'ghost' not in st.session_state: st.session_state.ghost = ""
if 'explanation' not in st.session_state: st.session_state.explanation = ""
if 'passed' not in st.session_state: st.session_state.passed = False

# --- 3. HARDENED API RELAY (500 ERROR FIX) ---
def call_oracle(payload, use_json_mode=True):
    headers = {"Authorization": f"Bearer {st.secrets['HS_API_KEY']}", "Content-Type": "application/json"}
    # If standard JSON mode fails, we move it to the prompt only
    if not use_json_mode and "response_format" in payload:
        del payload["response_format"]
        
    try:
        r = requests.post(f"{st.secrets['HS_BASE_URL']}/chat/completions", json=payload, headers=headers, timeout=35)
        if r.status_code == 500:
            # Fallback for Nginx/Server errors: try without strict JSON mode
            return call_oracle(payload, use_json_mode=False)
        if r.status_code != 200:
            st.error(f"Oracle Error {r.status_code}"); st.code(r.text); return None
        return r.json()['choices'][0]['message']['content']
    except Exception as e:
        st.error(f"Connection Failed: {str(e)}"); return None

# --- 4. THE GREAT HALL (UI) ---
st.set_page_config(page_title="The Thinking Chest", layout="wide")
st.markdown("""
    <style>
    .stCanvas { 
        background-color: #1a1c23 !important;
        background-image: linear-gradient(#2d313a 1px, transparent 1px) !important;
        background-size: 100% 40px !important;
        border: 3px solid #444; border-radius: 12px;
    }
    canvas { filter: drop-shadow(0 0 5px #ffffff); } /* Glowing Ink Effect */
    </style>
""", unsafe_allow_html=True)

# --- 5. SIDEBAR: IDENTITY & ARMOURY ---
name = st.sidebar.radio("Identify Scribe:", ["Ollie", "Liam"])
user = get_profile(name)
track = st.sidebar.radio("Learning Track:", ["English Master", "Mandarin Scribe"])

with st.sidebar:
    st.divider()
    st.metric("Ink Drops", f"{user['drops']} 💧")
    
    # INK SELECTION (Clean)
    st.subheader("🖋️ Current Ink")
    selected_ink_name = st.selectbox("Select from Collection", list(user['unlocked_inks'].keys()))
    user['active_ink_name'] = selected_ink_name
    user['active_ink_hex'] = user['unlocked_inks'][selected_ink_name]
    
    # THE ARMOURY SHOP
    with st.expander("⚔️ The Armoury ink shop"):
        tier_label = st.selectbox("Browse Tier", list(INK_CATALOG.keys()))
        price = 250 if "Common" in tier_label else 1000 if "Rare" in tier_label else 2500 if "Magic" in tier_label else 10000
        
        inks_in_tier = INK_CATALOG[tier_label]
        target_ink = st.selectbox("Select Pigment", list(inks_in_tier.keys()))
        hex_val = inks_in_tier[target_ink]
        
        st.markdown(f"**Cost:** {price} 💧")
        if st.button(f"Acquire {target_ink}"):
            if user['drops'] >= price:
                if target_ink not in user['unlocked_inks']:
                    user['drops'] -= price
                    user['unlocked_inks'][target_ink] = hex_val
                    save_profile(user); st.success(f"{target_ink} is yours!"); st.rerun()
                else: st.info("You already possess this ink.")
            else: st.error("You need more Ink Drops.")

    with st.expander("🔐 Coordinator"):
        if st.text_input("Key", type="password") == "67":
            if st.button("Add 10000💧"): user['drops'] += 10000; save_profile(user); st.rerun()

# --- 6. THE QUEST ---
st.title(f"🏰 {track}: Level {user['week_idx'] + 1}")

if not st.session_state.quest:
    # UPDATED: Choose your Quest
    st.session_state.choice = st.radio("Choose your Quest:", ["Creative Tale", "Logical Analysis", "Survival Skill"], horizontal=True)
    if st.button("🔓 Open the Scroll"):
        with st.spinner("Oracle is writing..."):
            instr = f"Track: {track}. Style: {st.session_state.choice}. User: {user['name']}. Task: Grade 6/HSK Challenge."
            payload = {"model": "gemini-3.1-pro-preview", "messages": [{"role": "system", "content": instr}]}
            res = call_oracle(payload)
            if res:
                st.session_state.quest = res; st.rerun()

if st.session_state.quest:
    st.info(st.session_state.quest)
    
    # PAPER PILOT
    with st.expander("📷 Paper Pilot (Camera Scan)"):
        cam = st.camera_input("Snapshot your paper")
        if cam and st.button("Analyze Ink"):
            with st.spinner("Decoding..."):
                encoded = base64.b64encode(cam.getvalue()).decode('utf-8')
                payload = {
                    "model": "gemini-3.1-flash-image-preview",
                    "messages": [{"role": "user", "content": [
                        {"type": "text", "text": "Return JSON: 'corrected', 'explanation', 'passed'."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded}"}}
                    ]}], "response_format": {"type": "json_object"}
                }
                res_str = call_oracle(payload)
                if res_str:
                    try:
                        # Clean potential markdown from raw text fallback
                        clean_str = res_str.replace("```json", "").replace("```", "").strip()
                        res = json.loads(clean_str)
                        st.session_state.ghost = res.get('corrected', "")
                        st.session_state.explanation = res.get('explanation', "")
                        st.rerun()
                    except: st.error("Oracle spoke in riddles. Try again.")

    # COUNSEL & AUDIO
    if st.session_state.explanation:
        c1, c2 = st.columns([4, 1])
        c1.success(f"📜 **The Master's Counsel:** {st.session_state.explanation}")
        with c2:
            if st.button("🔊 Hear Oracle"):
                tts = gTTS(text=st.session_state.explanation, lang='zh-CN' if track == "Mandarin Scribe" else 'en')
                fp = io.BytesIO(); tts.write_to_fp(fp); fp.seek(0); st.audio(fp, format='audio/mp3')

    # THE CANVAS
    opac = 0.15 if not st.session_state.passed else 0.45
    st.markdown(f'<p style="color:rgba(255,255,255,{opac}); font-family:Courier; font-size:30px; margin-bottom:-45px; padding-left:20px; font-weight:bold; pointer-events:none; line-height:40px;">{st.session_state.ghost}</p>', unsafe_allow_html=True)

    canvas_key = f"v53_{track}_{user['week_idx']}_{user['daily_count']}"
    canvas_result = st_canvas(stroke_width=4, stroke_color=user['active_ink_hex'], background_color="rgba(0,0,0,0)", height=500, key=canvas_key)

    colA, colB = st.columns(2)
    if colA.button("🔍 Check iPad Scribing"):
        if canvas_result.image_data is not None:
            img = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA').convert("RGB")
            buf = io.BytesIO(); img.save(buf, format="JPEG")
            encoded = base64.b64encode(buf.getvalue()).decode('utf-8')
            with st.spinner("Evaluating..."):
                payload = {
                    "model": "gemini-3.1-flash-image-preview",
                    "messages": [{"role": "user", "content": [
                        {"type": "text", "text": "Evaluate. Return JSON: 'corrected', 'explanation', 'passed'."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded}"}}
                    ]}], "response_format": {"type": "json_object"}
                }
                res_str = call_oracle(payload)
                if res_str:
                    try:
                        clean_str = res_str.replace("```json", "").replace("```", "").strip()
                        res = json.loads(clean_str)
                        st.session_state.ghost, st.session_state.explanation, st.session_state.passed = res.get('corrected', ""), res.get('explanation', ""), res.get('passed', False)
                        st.rerun()
                    except: st.error("JSON Error.")

    if st.session_state.passed:
        if colB.button("✨ Seal the Chest"):
            user['drops'] += 150 * (2 if track == "Mandarin Scribe" else 1)
            user['daily_count'] += 1
            if user['daily_count'] >= 3:
                user['daily_count'] = 0; user['week_idx'] += 1; st.balloons()
            save_profile(user)
            # Reset
            for k in ['quest', 'passed', 'ghost', 'explanation']: 
                st.session_state[k] = False if k in ['quest', 'passed'] else ""
            st.rerun()