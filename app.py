import streamlit as st
import requests, base64, json, os, io
from PIL import Image

# --- 0. LIBRARY SAFETY CHECK ---
try:
    from streamlit_drawable_canvas import st_canvas
    from streamlit_mic_recorder import mic_recorder
    from gtts import gTTS
    LIBS_OK = True
except ImportError as e:
    LIBS_OK = False
    ERR = str(e)

# --- 1. THE ARMOURY REGISTRY ---
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
        data = json.load(open(path, 'r'))
        for k, v in defaults.items():
            if k not in data: data[k] = v
        return data
    return defaults

def save_profile(data):
    json.dump(data, open(f"{data['name'].lower()}_vault.json", 'w'))

# --- 2. SESSION STATE MANAGEMENT ---
# Using a dictionary to batch-initialize
states = {
    'quest': False, 'ghost': "", 'explanation': "", 
    'passed': False, 'choice': "Creative Tale", 'debug_mode': False
}
for k, v in states.items():
    if k not in st.session_state: st.session_state[k] = v

# --- 3. HARDENED API RELAY (NO RECURSION) ---
def call_oracle(payload):
    headers = {
        "Authorization": f"Bearer {st.secrets['HS_API_KEY']}", 
        "Content-Type": "application/json"
    }
    
    if st.session_state.debug_mode:
        with st.expander("🛠️ Outgoing Payload Diagnostics"):
            st.json(payload)

    try:
        # Increased timeout for international routing (Xiamen to HS)
        r = requests.post(
            f"{st.secrets['HS_BASE_URL']}/chat/completions", 
            json=payload, headers=headers, timeout=45
        )
        
        if r.status_code != 200:
            st.error(f"Oracle Connection Error ({r.status_code})")
            st.code(r.text)
            # If the server 500s, we stop the execution to prevent infinite spinning
            st.stop()
            return None
            
        return r.json()['choices'][0]['message']['content']
        
    except Exception as e:
        st.error(f"The scroll failed to reach the tower: {str(e)}")
        return None

# --- 4. UI CONFIG & GLOWING CSS ---
st.set_page_config(page_title="The Thinking Chest", layout="wide")

# Determine glow intensity based on ink rarity
glow_color = st.session_state.get('active_ink_hex', '#FFFFFF')

st.markdown(f"""
    <style>
    .stCanvas {{ 
        background-color: #1a1c23 !important;
        background-image: linear-gradient(#2d313a 1px, transparent 1px) !important;
        background-size: 100% 40px !important;
        border: 3px solid #444; border-radius: 12px;
    }}
    /* The Glowing Ink Effect */
    canvas {{ filter: drop-shadow(0 0 6px {glow_color}); }} 
    </style>
""", unsafe_allow_html=True)

# --- 5. SIDEBAR: IDENTITY & THE ARMOURY ---
name = st.sidebar.radio("Identify Scribe:", ["Ollie", "Liam"])
user = get_profile(name)
track = st.sidebar.radio("Learning Track:", ["English Master", "Mandarin Scribe"])

with st.sidebar:
    st.divider()
    st.metric("Ink Drops", f"{user['drops']} 💧")
    
    # Clean Ink Selection
    st.subheader("🖋️ Collection")
    selected_ink = st.selectbox("Select Ink", list(user['unlocked_inks'].keys()))
    user['active_ink_name'] = selected_ink
    user['active_ink_hex'] = user['unlocked_inks'][selected_ink]
    # Update global glow for the CSS
    st.session_state['active_ink_hex'] = user['active_ink_hex']
    
    # THE ARMOURY SHOP
    st.markdown("### ⚔️ The Armoury ink shop")
    with st.expander("View Inks & Tiers"):
        tier_label = st.selectbox("Browse Tier", list(INK_CATALOG.keys()))
        
        # Explicit Pricing logic
        if "Common" in tier_label: price = 250
        elif "Rare" in tier_label: price = 1000
        elif "Magic" in tier_label: price = 2500
        else: price = 10000 # Legendary
        
        inks_in_tier = INK_CATALOG[tier_label]
        target_ink = st.selectbox("Choose Pigment", list(inks_in_tier.keys()))
        hex_val = inks_in_tier[target_ink]
        
        st.markdown(f"**Investment:** {price} 💧")
        if st.button(f"Forge {target_ink}"):
            if user['drops'] >= price:
                if target_ink not in user['unlocked_inks']:
                    user['drops'] -= price
                    user['unlocked_inks'][target_ink] = hex_val
                    save_profile(user)
                    st.success(f"The {target_ink} is yours."); st.rerun()
                else: st.info("This ink is already in your inventory.")
            else: st.error("You require more drops.")

    # Maintenance & Debug
    st.divider()
    st.session_state.debug_mode = st.toggle("Oracle Diagnostics")
    if st.button("🔄 Clear Stuck Scroll"):
        st.session_state.quest = False; st.rerun()

# --- 6. THE QUEST LOGIC ---
st.title(f"🏰 {track}: Level {user['week_idx'] + 1}")

if not st.session_state.quest:
    st.session_state.choice = st.radio("Choose your Quest:", ["Creative Tale", "Logical Analysis", "Survival Skill"], horizontal=True)
    
    if st.button("🔓 Open the Scroll"):
        with st.spinner("The Oracle is preparing the scroll..."):
            instr = f"User: {user['name']}. Track: {track}. Style: {st.session_state.choice}. Task: Grade 6 Level Challenge. Direct, no intro."
            payload = {
                "model": "gemini-3.1-pro-preview", 
                "messages": [{"role": "system", "content": instr}]
            }
            res = call_oracle(payload)
            if res:
                st.session_state.quest = res
                st.rerun()

# --- 7. ACTIVE QUEST UI ---
if st.session_state.quest:
    st.info(st.session_state.quest)
    
    # PAPER PILOT (Physical to Digital)
    with st.expander("📷 Paper Pilot (Camera Scan)"):
        cam = st.camera_input("Snapshot your physical draft")
        if cam and st.button("Extract Ink"):
            with st.spinner("Decoding..."):
                encoded = base64.b64encode(cam.getvalue()).decode('utf-8')
                # Safety: Using non-strict JSON for initial extraction
                payload = {
                    "model": "gemini-3.1-flash-image-preview",
                    "messages": [{"role": "user", "content": [
                        {"type": "text", "text": "Return strictly as JSON with keys 'corrected', 'explanation', 'passed' (true/false)."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded}"}}
                    ]}]
                }
                res_str = call_oracle(payload)
                if res_str:
                    try:
                        # Strip markdown if model returns it
                        json_data = json.loads(res_str.replace("```json", "").replace("```", "").strip())
                        st.session_state.ghost = json_data.get('corrected', "")
                        st.session_state.explanation = json_data.get('explanation', "")
                        st.rerun()
                    except: st.error("Oracle spoke in a format we cannot read. Try again.")

    # COUNSEL & AUDIO
    if st.session_state.explanation:
        c1, c2 = st.columns([4, 1])
        c1.success(f"📜 **The Master's Counsel:** {st.session_state.explanation}")
        with c2:
            if st.button("🔊 Hear Oracle"):
                tts = gTTS(text=st.session_state.explanation, lang='zh-CN' if track == "Mandarin Scribe" else 'en')
                fp = io.BytesIO(); tts.write_to_fp(fp); fp.seek(0)
                st.audio(fp, format='audio/mp3')

    # TRACING & CANVAS
    opac = 0.15 if not st.session_state.passed else 0.45
    st.markdown(f'<p style="color:rgba(255,255,255,{opac}); font-family:Courier; font-size:32px; margin-bottom:-45px; padding-left:20px; font-weight:bold; pointer-events:none; line-height:40px;">{st.session_state.ghost}</p>', unsafe_allow_html=True)

    c_key = f"v54_{track}_{user['week_idx']}_{user['daily_count']}"
    canvas_res = st_canvas(
        stroke_width=4, stroke_color=user['active_ink_hex'], 
        background_color="rgba(0,0,0,0)", height=500, key=c_key
    )

    colA, colB = st.columns(2)
    if colA.button("🔍 Check iPad Scribing"):
        if canvas_res.image_data is not None:
            img = Image.fromarray(canvas_res.image_data.astype('uint8'), 'RGBA').convert("RGB")
            buf = io.BytesIO(); img.save(buf, format="JPEG")
            encoded = base64.b64encode(buf.getvalue()).decode('utf-8')
            with st.spinner("Calculating precision..."):
                payload = {
                    "model": "gemini-3.1-flash-image-preview",
                    "messages": [{"role": "user", "content": [
                        {"type": "text", "text": "Evaluate tracing. Return JSON: 'corrected', 'explanation', 'passed'."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded}"}}
                    ]}]
                }
                res_str = call_oracle(payload)
                if res_str:
                    try:
                        json_data = json.loads(res_str.replace("```json", "").replace("```", "").strip())
                        st.session_state.ghost = json_data.get('corrected', "")
                        st.session_state.explanation = json_data.get('explanation', "")
                        st.session_state.passed = json_data.get('passed', False)
                        st.rerun()
                    except: st.error("Evaluation error.")

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