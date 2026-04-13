import streamlit as st
from streamlit_drawable_canvas import st_canvas
import json
import os

# --- 1. DATA PERSISTENCE ---
def load_data():
    if not os.path.exists('database.json'):
        return {"mastery_score": 50, "ink_drops": 100, "inventory": ["Pencil"]}
    with open('database.json', 'r') as f:
        return json.load(f)

def save_data(data):
    with open('database.json', 'w') as f:
        json.dump(data, f)

# Initialize Session State
if 'data' not in st.session_state:
    st.session_state.data = load_data()

# --- 2. SIDEBAR STATUS (The "IXL" Mastery Bar) ---
st.sidebar.title("🖋️ Scribe Mastery")
st.sidebar.metric("Ink Drops", f"{st.session_state.data['ink_drops']} 💧")
st.sidebar.progress(st.session_state.data['mastery_score'] / 100)
st.sidebar.write(f"Mastery Level: {st.session_state.data['mastery_score']}%")

# --- 3. MAIN INTERFACE ---
st.title("🏰 Daily Writing Quest")
st.subheader("Today's Prompt:")
st.info("If you could turn your brother into any animal for one day, what would it be and why?")

# The Writing Canvas (iPad friendly)
st.write("---")
st.write("### Write here with your Apple Pencil:")
canvas_result = st_canvas(
    fill_color="rgba(255, 165, 0, 0.3)",
    stroke_width=2,
    stroke_color="#000000",
    background_color="#ffffff",
    height=300,
    drawing_mode="freedraw",
    key="canvas",
)

# --- 4. THE AUDIT (The "Hard" Sage) ---
if st.button("Submit to the Master Scribe"):
    # Simulated AI Audit for now
    # In a real run, we'd send canvas_result.image_data to Holy Sheep AI
    
    # LAZY TEST: Let's assume they were lazy today for testing the -3x penalty
    is_lazy = True 
    
    if is_lazy:
        # THE IXL PENALTY: -6 points (3x the usual 2 point gain)
        st.session_state.data['mastery_score'] = max(0, st.session_state.data['mastery_score'] - 6)
        st.session_state.data['ink_drops'] = max(0, st.session_state.data['ink_drops'] - 30)
        save_data(st.session_state.data)
        
        st.error("❌ LAZY INK DETECTED!")
        st.write("The Master Scribe is disappointed. Your letters are floating. You lost 30 💧 and your Mastery dropped.")
        st.warning("RE-WRITE the first word to regain your status.")
    else:
        st.balloons()
        st.success("✅ DISCIPLINED WRITING!")
        st.session_state.data['mastery_score'] = min(100, st.session_state.data['mastery_score'] + 2)
        st.session_state.data['ink_drops'] += 10
        save_data(st.session_state.data)