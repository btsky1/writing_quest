import streamlit as st
import requests, base64, json, os, io
from PIL import Image

# --- 0. SAFE IMPORTS ---
try:
    from streamlit_drawable_canvas import st_canvas
    from streamlit_mic_recorder import mic_recorder
    from gtts import gTTS
    LIBS_OK = True
except:
    LIBS_OK = False

# --- 1. DATA & ECONOMY ENGINE ---
def get_profile(name):
    path = f"{name.lower()}_vault.json"
    defaults = {
        "name": name, "drops": 100, "week_idx": 0, "daily_count": 0, 
        "en_maxed": False, "story_context": "The journey begins...", 
        "active_ink": "#ffffff", "xp": {"precision": 10},
        "unlocked_inks": ["#ffffff", "#000000", "#FFD700"] # Starter: White, Midnight, Gold
    }
    if os.path.exists(path):
        data = json.load(open(path, 'r'))
        for k, v in defaults.items():
            if k not in data: data[k] = v
        return data
    return defaults

def save_profile(data):
    json.dump(data, open(f"{data['name'].lower()}_vault.json", 'w'))

# --- 2. INITIALIZE SESSION STATES ---
state_keys = {'quest': False, 'ghost': "", 'explanation': "", 'passed': False}
for key, val in state_keys.items():
    if key not in st.session_state:
        st.session_state[key] = val

# --- 3. VISION & QUEST ENGINE ---
def call_oracle(payload, endpoint="chat/completions"):
    headers = {"Authorization": f"Bearer {st.secrets['HS_API_KEY']}", "Content-Type": "application/json"}
    try:
        r = requests.post(f"{st.secrets['HS_BASE_URL']}/{endpoint}", json=payload, headers=headers, timeout=25)
        response_data = r.json()
        if 'choices' in response_data:
            return response_data['choices'][0]['message']['content']
        else:
            st.error(f"Oracle Error: {response_data.get('error', 'Unknown Error')}")
            return None
    except Exception as e:
        st.error(f"Connection Error: {str(e)}")
        return None

# --- 4. UI CONFIG & STYLING ---
st.set_page_config(page_title="The Thinking Chest", layout="wide")
if not LIBS_OK:
    st.error("⚠️ Library Error. Check requirements.txt"); st.stop()

st.markdown(f"""
    <style>
    .stCanvas {{ 
        background-color: #1a1c23 !important;
        background-image: linear-gradient(#2d313a 1px, transparent 1px) !important;
        background-size: 100% 40px !important;
        border: 3px solid #444; border-radius: 10px;
    }}
    canvas {{ filter: drop-shadow(0 0 2px #ffffff); }} /* Moonlight Glow */
    </style>
""", unsafe_allow_html=True)

# --- 5. SIDEBAR: ECONOMY & TOOLS ---
name = st.sidebar.radio("Scribe:", ["Ollie", "Liam"])
user = get_profile(name)
track = st.sidebar.radio("Track:", ["English Master", "Mandarin Scribe"])

with st.sidebar:
    st.divider()
    st.metric("Ink Drops", f"{user['drops']} 💧")
    
    # INK SELECTION
    st.subheader("🖋️ Ink Well")
    user['active_ink'] = st.color_picker("Dip Pen", user.get('active_ink', '#ffffff'))
    
    # INK SHOP
    with st.expander("🛍️ Buy New Inks"):
        new_color = st.color_picker("Discover Rare Pigment", "#FF00FF")
        if st.button(f"Unlock for 500 💧"):
            if user['drops'] >= 500:
                user['drops'] -= 500
                user['unlocked_inks'].append(new_color)
                save_profile(user); st.success("Pigment Unlocked!"); st.rerun()
            else: st.error("Not enough Drops.")

    with st.expander("🔐 Coordinator"):
        if st.text_input("Code", type="password") == "67":
            if st.button("Grant 1000 Drops"): 
                user['drops'] += 1000; save_profile(user); st.rerun()

# --- 6. THE QUEST ---
st.title(f"🏰 {track}: Level {user['week_idx'] + 1}")

if not st.session_state.quest:
    if st.button("🔓 Open the Scroll"):
        payload = {
            "model": "gemini-3.1-flash",
            "messages": [{"role": "system", "content": f"Context: {user['story_context']}. Track: {track}. Task: G6 English or HSK Mandarin."}]
        }
        res = call_oracle(payload)
        if res:
            st.session_state.quest = res
            st.rerun()

if st.session_state.quest:
    st.info(st.session_state.quest)
    
    # 📷 PAPER PILOT
    with st.expander("📷 Use Paper Pilot (Camera)"):
        cam = st.camera_input("Scan your paper draft")
        if cam:
            with st.spinner("Decoding your grit..."):
                headers = {"Authorization": f"Bearer {st.secrets['HS_API_KEY']}"}
                encoded = base64.b64encode(cam.getvalue()).decode('utf-8')
                payload = {
                    "model": "gemini-3.1-flash-image-preview",
                    "messages": [{"role": "user", "content": [
                        {"type": "text", "text": f"Evaluate work for {user['name']}. Return JSON: 'corrected', 'explanation', 'passed'."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded}"}}
                    ]}], "response_format": {"type": "json_object"}
                }
                r = requests.post(f"{st.secrets['HS_BASE_URL']}/chat/completions", json=payload, headers=headers).json()
                res = json.loads(r['choices'][0]['message']['content'])
                st.session_state.ghost, st.session_state.explanation = res.get('corrected', ""), res.get('explanation', "")
                st.rerun()

    # THE COUNSEL & AUDIO
    if st.session_state.explanation:
        st.success(f"📜 **The Master's Counsel:** {st.session_state.explanation}")
        if st.button("🔊 Hear Oracle"):
            tts = gTTS(text=st.session_state.explanation, lang='zh-CN' if track == "Mandarin Scribe" else 'en')
            fp = io.BytesIO(); tts.write_to_fp(fp); fp.seek(0)
            st.audio(fp, format='audio/mp3')

    # THE CANVAS
    opacity = 0.15 if not st.session_state.passed else 0.45
    st.markdown(f'<p style="color:rgba(255,255,255,{opacity}); font-family:Courier; font-size:32px; margin-bottom:-45px; padding-left:20px; font-weight:bold; pointer-events:none;">{st.session_state.ghost}</p>', unsafe_allow_html=True)

    canvas_key = f"v40_{track}_{user['week_idx']}_{user['daily_count']}"
    canvas_result = st_canvas(stroke_width=4, stroke_color=user['active_ink'], background_color="rgba(0,0,0,0)", height=500, key=canvas_key)

    c1, c2 = st.columns(2)
    if c1.button("🔍 Check iPad Scribing"):
        if canvas_result.image_data is not None:
            img = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA').convert("RGB")
            buf = io.BytesIO(); img.save(buf, format="JPEG")
            encoded = base64.b64encode(buf.getvalue()).decode('utf-8')
            payload = {
                "model": "gemini-3.1-flash-image-preview",
                "messages": [{"role": "user", "content": [
                    {"type": "text", "text": f"Scribe: {user['name']}. Track: {track}. Return JSON: 'corrected', 'explanation', 'passed'."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded}"}}
                ]}], "response_format": {"type": "json_object"}
            }
            res_str = call_oracle(payload)
            if res_str:
                res = json.loads(res_str)
                st.session_state.ghost, st.session_state.explanation, st.session_state.passed = res.get('corrected', ""), res.get('explanation', ""), res.get('passed', False)
                st.rerun()

    if st.session_state.passed:
        if c2.button("✨ Seal the Chest"):
            user['drops'] += 150 * (2 if track == "Mandarin Scribe" else 1)
            user['daily_count'] += 1
            if user['daily_count'] >= 3:
                user['daily_count'] = 0; user['week_idx'] += 1; st.balloons()
            save_profile(user)
            for k in state_keys.keys(): st.session_state[k] = state_keys[k]
            st.rerun()