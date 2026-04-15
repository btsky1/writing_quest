import streamlit as st
from streamlit_drawable_canvas import st_canvas
from streamlit_mic_recorder import mic_recorder
import requests, base64, json, os, io
from PIL import Image
from gtts import gTTS # pip install gTTS

# --- 1. CORE ENGINE ---
def get_profile(name):
    path = f"{name.lower()}_vault.json"
    if os.path.exists(path): return json.load(open(path, 'r'))
    return {"name": name, "drops": 100, "week_idx": 0, "daily_count": 0, "en_maxed": False, "story_context": "The journey begins...", "active_ink": "#000000", "xp": {"precision": 10}, "unlocked_inks": ["#000000"]}

def save_profile(data):
    json.dump(data, open(f"{data['name'].lower()}_vault.json", 'w'))

# --- 2. VISION & AUDIO ENGINE ---
def analyze_work(image_bytes, user, mode):
    encoded_img = base64.b64encode(image_bytes).decode('utf-8')
    headers = {"Authorization": f"Bearer {st.secrets['HS_API_KEY']}", "Content-Type": "application/json"}
    payload = {
        "model": "gemini-3.1-flash-image-preview",
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": f"Evaluate {mode} for {user['name']}. Return JSON with 'corrected', 'explanation' (G6 logic), and 'passed' (bool)."},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_img}"}}
        ]}], "response_format": {"type": "json_object"}
    }
    try:
        r = requests.post(f"{st.secrets['HS_BASE_URL']}/chat/completions", json=payload, headers=headers, timeout=25)
        return json.loads(r.json()['choices'][0]['message']['content'])
    except: return {"corrected": "Error", "explanation": "Oracle Offline", "passed": False}

def speak(text, lang='en'):
    tts = gTTS(text=text, lang=lang)
    fp = io.BytesIO(); tts.write_to_fp(fp); fp.seek(0)
    st.audio(fp, format='audio/mp3')

# --- 3. UI SETUP ---
st.set_page_config(page_title="The Thinking Chest", layout="wide")
name = st.sidebar.radio("Scribe:", ["Ollie", "Liam"])
user = get_profile(name)

st.markdown(f"""
    <style>
    .stCanvas {{ background-color: #1a1c23; background-image: linear-gradient(#2d313a 1px, transparent 1px); background-size: 100% 40px; border: 3px solid #444; border-radius: 10px; }}
    canvas {{ filter: drop-shadow(0 0 2px #ffffff); }}
    </style>
""", unsafe_allow_html=True)

# --- 4. THE QUEST AREA ---
track = st.sidebar.radio("Path:", ["English Master", "Mandarin Scribe"])
st.title(f"🏰 {track}: Level {user['week_idx'] + 1}")

if "quest" not in st.session_state: st.session_state.quest = False

if not st.session_state.quest:
    if st.button("🔓 Open Scroll"):
        headers = {"Authorization": f"Bearer {st.secrets['HS_API_KEY']}"}
        prompt = f"Context: {user['story_context']}. Track: {track}."
        payload = {"model": "gemini-3.1-flash", "messages": [{"role": "system", "content": prompt}]}
        st.session_state.quest = requests.post(f"{st.secrets['HS_BASE_URL']}/chat/completions", json=payload, headers=headers).json()['choices'][0]['message']['content']
        st.rerun()

if st.session_state.quest:
    # THE PROMPT - Always visible at the top
    st.info(st.session_state.quest)
    
    # LIVE PAPER PILOT - Integrated right below the prompt
    with st.expander("📷 Use Paper Pilot (Camera)"):
        cam = st.camera_input("Scan your paper draft")
        if cam and st.button("Analyze Paper"):
            res = analyze_work(cam.getvalue(), user, track)
            st.session_state.ghost = res.get('corrected', "")
            st.session_state.explanation = res.get('explanation', "")
            st.success("Paper Draft loaded into the Ghost Model!")

    # THE COUNSEL & AUDIO
    if st.session_state.get('explanation'):
        c1, c2 = st.columns([4, 1])
        c1.success(f"📜 **The Master's Counsel:** {st.session_state.explanation}")
        with c2: 
            if st.button("🔊 Hear Counsel"): speak(st.session_state.explanation, 'zh-CN' if track == "Mandarin Scribe" else 'en')

    # THE CANVAS
    opacity = 0.15 if not st.session_state.get('passed') else 0.45
    st.markdown(f'<p style="color:rgba(255,255,255,{opacity}); font-family:Courier; font-size:32px; margin-bottom:-45px; padding-left:20px; font-weight:bold;">{st.session_state.get("ghost", "")}</p>', unsafe_allow_html=True)

    canvas_key = f"v37_{track}_{user['week_idx']}_{user['daily_count']}"
    canvas_result = st_canvas(stroke_width=4, stroke_color="#000000", background_color="rgba(0,0,0,0)", height=500, key=canvas_key)

    colA, colB = st.columns(2)
    if colA.button("🔍 Check iPad Scribing"):
        if canvas_result.image_data is not None:
            img = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA').convert("RGB")
            buf = io.BytesIO(); img.save(buf, format="JPEG")
            res = analyze_work(buf.getvalue(), user, track)
            st.session_state.ghost, st.session_state.explanation, st.session_state.passed = res.get('corrected', ""), res.get('explanation', ""), res.get('passed', False)
            st.rerun()

    if st.session_state.get('passed'):
        if colB.button("✨ Seal the Chest"):
            user['drops'] += 150 * (2 if track == "Mandarin Scribe" else 1)
            user['daily_count'] += 1
            if user['daily_count'] >= 3:
                user['daily_count'] = 0; user['week_idx'] += 1; st.balloons()
            save_profile(user)
            for k in ['quest', 'ghost', 'explanation', 'passed']: st.session_state[k] = False
            st.rerun()