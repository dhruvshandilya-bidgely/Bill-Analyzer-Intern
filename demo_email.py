# app1.py
import streamlit as st
from PIL import Image
import webbrowser

# Set Streamlit theme to light
st.set_page_config(layout="centered", page_title="Email", page_icon=":mail:")

# Display an image
image = Image.open('email_image.png')
st.image(image, use_column_width=True)