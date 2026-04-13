import streamlit as st
from streamlit_drawable_canvas import st_canvas
import json
import os

# --- 1. ACCESS SECRETS ---
# This pulls the key you just gave me from Streamlit's internal secrets
API_KEY = st.secrets["HOLY_SHEEP_API_KEY"]

# --- 2. DATA LOAD/SAVE ---
def load_data():
    if not os.path.exists('database.json'):
        return {"mastery": 50, "drops": 100, "inventory": ["Standard Pencil"]}
    with open('database.json', 'r') as f:
        return json.load(f)

def save_data(data):
    with open('database.json', 'w') as f:
        json.dump(data, f)

if 'data' not in st.session_state:
    st.session_state.data = load_data()

# --- 3. THE SHOP (UNLOCKS) ---
st.sidebar.title("🛍️ Scribe Emporium")
if st.session_state.data['drops'] >= 500 and "Neon Ink" not in st.session_state.data['inventory']:
    if st.sidebar.button("Buy Neon Ink (500 💧)"):
        st.session_state.data['drops'] -= 500
        st.session_state.data['inventory'].append("Neon Ink")
        save_data(st.session_state.data)
        st.sidebar.success("Unlocked: Neon!")

selected_gear = st.sidebar.selectbox("Equip Pen:", st.session_state.data['inventory'])
ink_color = "#39FF14" if selected_gear == "Neon Ink" else "#000000"

# --- 4. HUD & MASTERY ---
st.sidebar.divider()
st.sidebar.metric("Ink Drops", f"{st.session_state.data['drops']} 💧")
st.sidebar.write(f"**Mastery:** {st.session_state.data['mastery']}%")
st.sidebar.progress(st.session_state.data['mastery'] / 100)

# --- 5. THE QUEST ---
st.title("🏰 The Scribe's Quest")
st.info("QUEST: What is the secret ingredient in the world's most powerful potion?")

canvas_result = st_canvas(
    stroke_width=2,
    stroke_color=ink_color,
    background_color="#ffffff",
    height=300,
    drawing_mode="freedraw",
    key="canvas",
)

# --- 6. THE AUDIT (The Hard Mode) ---
if st.button("Submit to the Master Scribe"):
    # Simulated check: In real life, we'd send canvas_result.image_data to Holy Sheep
    # For now, we apply the 3x IXL penalty for testing
    is_lazy = True 
    
    if is_lazy:
        st.session_state.data['mastery'] = max(0, st.session_state.data['mastery'] - 6)
        st.session_state.data['drops'] = max(0, st.session_state.data['drops'] - 30)
        save_data(st.session_state.data)
        st.error("⚠️ LAZY INK! The foundation is shaky. -30 💧 Fine Applied.")
        st.warning("Trace your letters correctly to reclaim your honor.")
    else:
        st.balloons()
        st.session_state.data['mastery'] = min(100, st.session_state.data['mastery'] + 2)
        st.session_state.data['drops'] += 20
        save_data(st.session_state.data)