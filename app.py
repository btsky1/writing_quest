import streamlit as st
import requests, base64, json, os, io
from PIL import Image

# --- 0. SAFE IMPORTS ---
try:
    from streamlit_drawable_canvas import st_canvas
    from streamlit_mic_recorder import mic_recorder
    from gtts import gTTS
    LIBS_OK = True
except ImportError as e:
    LIBS_OK = False
    MISSING_LIB = str(e).split("'")[-2]

# --- 1. DATA ENGINE ---
def get_profile(name):
    path = f"{name.lower()}_vault.json"
    defaults = {
        "name": name, "drops": 100, "week_idx": 0, "daily_count": 0, 
        "en_maxed": False, "story_context": "The journey begins...", 
        "xp": {"precision": 10}
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

# --- 3. VISION & AUDIO ENGINE ---
def analyze_work(image_bytes, user, mode):
    encoded_img = base64.b64encode(image_bytes).decode('utf-8')
    headers = {"Authorization": f"Bearer {st.secrets['HS_API_KEY']}", "Content-Type": "application/json"}
    payload = {
        "model": "gemini-3.1-flash-image-preview",
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": f"Evaluate {mode} for {user['name']}. Return JSON: 'corrected', 'explanation' (G6 logic), 'passed' (bool)."},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_img}"}}
        ]}], "response_format": {"type": "json_object"}
    }
    try:
        r = requests.post(f"{st.secrets['HS_BASE_URL']}/chat/completions", json=payload, headers=headers, timeout=25)
        return json.loads(r.json()['choices'][0]['message']['content'])
    except: return {"corrected": "", "explanation": "Oracle connection timed out.", "passed": False}

# --- 4. UI CONFIG & STYLING ---
st.set_page_config(page_title="The Thinking Chest", layout="wide")

if not LIBS_OK:
    st.error(f"⚠️ **Deployment Error:** Missing library `{MISSING_LIB}`.")
    st.info("CEO: Please add `streamlit-mic-recorder` and `gTTS` to your `requirements.txt` on GitHub.")
    st.stop()

st.markdown(f"""
    <style>
    .stCanvas {{ 
        background-color: #1a1c23 !important;
        background-image: linear-gradient(#2d313a 1px, transparent 1px) !important;
        background-size: 100% 40px !important;
        border: 3px solid #444; border-radius: 10px;
    }}
    canvas {{ filter: drop-shadow(0 0 2px #ffffff); }}
    </style>
""", unsafe_allow_html=True)

# --- 5. THE QUEST ---
name = st.sidebar.radio("Scribe:", ["Ollie", "Liam"])
user = get_profile(name)
track = st.sidebar.radio("Track:", ["English Master", "Mandarin Scribe"])

st.title(f"🏰 {track}: Level {user['week_idx'] + 1}")

if not st.session_state.quest:
    if st.button("🔓 Open the Scroll"):
        headers = {"Authorization": f"Bearer {st.secrets['HS_API_KEY']}"}
        prompt = f"Context: {user['story_context']}. Track: {track}. Focus: G6 English or HSK Mandarin Survival."
        payload = {"model": "gemini-3.1-flash", "messages": [{"role": "system", "content": prompt}]}
        st.session_state.quest = requests.post(f"{st.secrets['HS_BASE_URL']}/chat/completions", json=payload, headers=headers).json()['choices'][0]['message']['content']
        st.rerun()

if st.session_state.quest:
    st.info(st.session_state.quest)
    
    # 📷 PAPER PILOT (LIVE CAMERA)
    with st.expander("📷 Use Paper Pilot (Camera)"):
        cam = st.camera_input("Scan your paper draft")
        if cam:
            with st.spinner("Decoding your physical grit..."):
                res = analyze_work(cam.getvalue(), user, track)
                st.session_state.ghost = res.get('corrected', "")
                st.session_state.explanation = res.get('explanation', "")
                st.rerun()

    # THE COUNSEL & ORACLE'S VOICE
    if st.session_state.explanation:
        c1, c2 = st.columns([4, 1])
        c1.success(f"📜 **The Master's Counsel:** {st.session_state.explanation}")
        with c2: 
            if st.button("🔊 Hear Counsel"):
                tts = gTTS(text=st.session_state.explanation, lang='zh-CN' if track == "Mandarin Scribe" else 'en')
                fp = io.BytesIO(); tts.write_to_fp(fp); fp.seek(0)
                st.audio(fp, format='audio/mp3')

    # THE CANVAS (With Luminous Ghost Text)
    opacity = 0.15 if not st.session_state.passed else 0.45
    st.markdown(f'<p style="color:rgba(255,255,255,{opacity}); font-family:Courier; font-size:32px; margin-bottom:-45px; padding-left:20px; font-weight:bold; pointer-events:none;">{st.session_state.ghost}</p>', unsafe_allow_html=True)

    canvas_key = f"v39_{track}_{user['week_idx']}_{user['daily_count']}"
    canvas_result = st_canvas(stroke_width=4, stroke_color="#000000", background_color="rgba(0,0,0,0)", height=500, key=canvas_key)

    c1, c2 = st.columns(2)
    if c1.button("🔍 Check iPad Scribing"):
        if canvas_result.image_data is not None:
            img = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA').convert("RGB")
            buf = io.BytesIO(); img.save(buf, format="JPEG")
            with st.spinner("Evaluating logic and strokes..."):
                res = analyze_work(buf.getvalue(), user, track)
                st.session_state.ghost = res.get('corrected', "")
                st.session_state.explanation = res.get('explanation', "")
                st.session_state.passed = res.get('passed', False)
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