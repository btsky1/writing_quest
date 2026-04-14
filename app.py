import streamlit as st
from streamlit_drawable_canvas import st_canvas
import json
import os
from PIL import Image
import numpy as np

# --- 1. CORE ENGINE ---
def load_curriculum():
    with open('curriculum.json', 'r') as f:
        return json.load(f)['curriculum']

def get_profile(name):
    path = f"{name.lower()}_vault_vfinal.json"
    if os.path.exists(path):
        with open(path, 'r') as f: return json.load(f)
    return {
        "name": name, "drops": 100, "week_idx": 0, "active_ink": "#000000",
        "xp": {"precision": 50, "logic": 50, "grit": 50},
        "inventory": ["Standard Ink"]
    }

def save_profile(data):
    with open(f"{data['name'].lower()}_vault_vfinal.json", 'w') as f: json.dump(data, f)

# Create gallery folder if it doesn't exist
if not os.path.exists("gallery"):
    os.makedirs("gallery")

# --- 2. UI SETUP ---
st.set_page_config(page_title="The Thinking Chest", layout="wide")
curr = load_curriculum()

name = st.sidebar.radio("Identify Scribe:", ["Ollie", "Liam"])
user = get_profile(name)

# Sidebar HUD
st.sidebar.title(f"🏰 {user['name']}'s Vault")
st.sidebar.metric("Ink Drops", f"{user['drops']} 💧")

# --- 3. MAIN INTERFACE TABS ---
tab_quest, tab_gallery = st.tabs(["🏹 Current Quest", "🖼️ Scribe Gallery"])

with tab_quest:
    active_week = curr[user['week_idx'] % len(curr)]
    st.header(f"Level {user['week_idx'] + 1}: {active_week['skill']}")

    col_logic, col_creative = st.columns(2)
    with col_logic:
        if st.button(f"🧠 LOGIC: {active_week['choices']['logic']['title']}"):
            st.session_state.choice = 'logic'
    with col_creative:
        if st.button(f"🎨 CREATIVE: {active_week['choices']['creative']['title']}"):
            st.session_state.choice = 'creative'

    if 'choice' in st.session_state:
        selected = active_week['choices'][st.session_state.choice]
        st.info(f"**QUEST:** {selected['prompt']}")
        
        # Adaptive Canvas
        lh = 50 if user['xp']['precision'] < 75 else 40
        st.markdown(f"<style>.stCanvas {{ border: 4px solid #31333F; background-image: linear-gradient(#e1e1e1 2px, transparent 1px); background-size: 100% {lh}px; }}</style>", unsafe_allow_html=True)

        canvas_result = st_canvas(
            stroke_width=3, stroke_color=user['active_ink'],
            background_color="#ffffff", height=500, key=f"{name}_w{user['week_idx']}"
        )

        if st.button("Seal the Chest"):
            # 1. Save the Image to Gallery
            if canvas_result.image_data is not None:
                img_path = f"gallery/{name.lower()}_level_{user['week_idx']+1}.png"
                # Convert canvas data to a savable image
                img = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')
                img.save(img_path)

            # 2. Update Stats (using standard reward logic)
            p, l, g = 85, 90, 100 # Adjust these or add sliders for manual audit
            user['xp']['precision'] = (user['xp']['precision'] + p) // 2
            user['xp']['logic'] = (user['xp']['logic'] + l) // 2
            user['xp']['grit'] = (user['xp']['grit'] + g) // 2
            user['drops'] += (g // 2) + 25
            
            if (user['xp']['precision'] + user['xp']['logic'] + user['xp']['grit']) / 3 > active_week['mastery_score']:
                user['week_idx'] += 1
                st.balloons()
            
            save_profile(user)
            del st.session_state.choice
            st.rerun()

with tab_gallery:
    st.header(f"The Chronicles of {user['name']}")
    
    # Fetch all images for this specific user
    user_images = [f for f in os.listdir("gallery") if f.startswith(name.lower())]
    user_images.sort() # Keeps them in Level order

    if not user_images:
        st.write("Your gallery is empty. Complete a quest to start your collection!")
    else:
        # Display images in a 3-column grid
        cols = st.columns(3)
        for i, img_name in enumerate(user_images):
            with cols[i % 3]:
                st.image(f"gallery/{img_name}", caption=f"Level {i+1}", use_container_width=True)