import os
import sys
import time
from pathlib import Path
from datetime import datetime

import streamlit as st
import pandas as pd
from PIL import Image

import io
import base64
import streamlit.components.v1 as components

# Add current workspace to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

CANVAS_DIR = Path(__file__).resolve().parent / "canvas_component"
canvas_editor_component = components.declare_component("canvas_editor", path=str(CANVAS_DIR))

from config import DATA_DIR, UPLOADS_DIR, SAVED_DIR, DB_PATH
from database import init_db, save_document, list_documents, get_document, delete_document
from pdf_engine import (
    get_pdf_page_count,
    render_pdf_page_image,
    extract_page_text_blocks,
    apply_edits_and_export
)

# Page Setup: Clean Full-Width View without Sidebar Clutter
st.set_page_config(
    page_title="PDF Invoice Visual Editor",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Initialize Database
init_db()


def reset_document_state():
    """Completely resets active document and purges all cached input fields."""
    st.session_state.current_pdf_bytes = None
    st.session_state.current_pdf_name = None
    st.session_state.current_page_idx = 0
    st.session_state.active_edits = []
    st.session_state.preview_bytes = None
    st.session_state["uploaded_via_uploader"] = False

    # Purge all cached form input keys to prevent any cross-document bleed
    keys_to_clear = [k for k in list(st.session_state.keys()) if k.startswith("input_") or k == "top_save_title_input"]
    for k in keys_to_clear:
        del st.session_state[k]

# Session State Initialization
if "theme" not in st.session_state:
    st.session_state.theme = "dark"
if "current_pdf_bytes" not in st.session_state:
    st.session_state.current_pdf_bytes = None
if "current_pdf_name" not in st.session_state:
    st.session_state.current_pdf_name = None
if "current_page_idx" not in st.session_state:
    st.session_state.current_page_idx = 0
if "active_edits" not in st.session_state:
    st.session_state.active_edits = []
if "preview_bytes" not in st.session_state:
    st.session_state.preview_bytes = None
if "view_mode" not in st.session_state:
    st.session_state.view_mode = "dashboard" if len(list_documents()) > 0 else "editor"

# Custom Styling: Complete Removal of 3-Dots, Deploy Button & Clutter + Dark/Light Theme
is_dark = (st.session_state.theme == "dark")

theme_css = f"""
<style>
    /* 1. Complete Removal of 3 dots menu, Deploy button, and Header chrome */
    #MainMenu {{ visibility: hidden !important; display: none !important; }}
    header {{ visibility: hidden !important; display: none !important; height: 0 !important; }}
    footer {{ visibility: hidden !important; display: none !important; }}
    .stAppDeployButton {{ display: none !important; }}
    [data-testid="stAppDeployButton"] {{ display: none !important; }}
    [data-testid="stToolbar"] {{ display: none !important; visibility: hidden !important; }}
    [data-testid="stDecoration"] {{ display: none !important; }}
    [data-testid="stStatusWidget"] {{ display: none !important; }}
    [data-testid="collapsedControl"] {{ display: none !important; }}
    section[data-testid="stSidebar"] {{ display: none !important; }}

    .block-container {{
        padding-top: 1.5rem !important;
        padding-bottom: 2rem !important;
    }}

    /* 2. Dark / Light Dynamic Theme with Full Readability */
    {'''
    .stApp {
        background-color: #0E1117 !important;
        color: #E6EDF3 !important;
    }
    .app-title {
        font-size: 24px;
        font-weight: 700;
        color: #F0F6FC !important;
        margin-bottom: 2px;
    }
    .app-subtitle {
        font-size: 13px;
        color: #8B949E !important;
        margin-bottom: 12px;
    }
    h1, h2, h3, h4, h5, h6, p, span, div {
        color: #E6EDF3;
    }
    .stMarkdown p, .stMarkdown span {
        color: #E6EDF3 !important;
    }
    /* Labels & Captions */
    label, [data-testid="stWidgetLabel"] p {
        color: #F0F6FC !important;
        font-weight: 600 !important;
    }
    .stCaption, small {
        color: #8B949E !important;
    }
    /* Inputs */
    div[data-baseweb="input"], div[data-baseweb="base-input"], .stTextInput > div > div {
        background-color: #161B22 !important;
        border: 1px solid #30363D !important;
        border-radius: 6px !important;
        color: #F0F6FC !important;
    }
    input, textarea {
        background-color: transparent !important;
        color: #F0F6FC !important;
        caret-color: #F0F6FC !important;
    }
    input::placeholder {
        color: #6E7681 !important;
    }
    /* File Uploader Dropzone & Uploaded File Items in Dark Mode */
    [data-testid="stFileUploader"], [data-testid="stFileUploaderDropzone"], [data-testid="stFileUploader"] section {
        background-color: #161B22 !important;
        border: 2px dashed #30363D !important;
        border-radius: 8px !important;
        color: #F0F6FC !important;
    }
    [data-testid="stFileUploaderDropzone"] *, [data-testid="stFileUploader"] section * {
        color: #F0F6FC !important;
    }
    /* Specific styling for the uploaded file pill/card in Dark Mode */
    [data-testid="stFileUploaderDropzone"] [data-testid*="File"],
    [data-testid="stFileUploader"] [data-testid*="File"],
    [data-testid="stFileUploader"] section > div,
    [data-testid="stFileUploaderDropzone"] > div,
    [data-testid="stFileUploaderDropzone"] ul,
    [data-testid="stFileUploaderDropzone"] li,
    [data-testid="stFileUploaderDropzone"] div[target] {
        background-color: #21262D !important;
        border: 1px solid #30363D !important;
        border-radius: 6px !important;
        color: #F0F6FC !important;
    }
    [data-testid="stFileUploaderDropzone"] button, [data-testid="stFileUploader"] section button {
        background-color: #21262D !important;
        color: #F0F6FC !important;
        border: 1px solid #30363D !important;
    }
    [data-testid="stFileUploaderDropzone"] button *, [data-testid="stFileUploader"] svg {
        color: #F0F6FC !important;
        fill: #F0F6FC !important;
    }
    /* Fullscreen Button / Image Toolbar in Dark Mode */
    [data-testid="stElementToolbar"],
    [data-testid="stElementToolbarButton"],
    button[title="View fullscreen"],
    button[aria-label="View fullscreen"],
    button[aria-label="Fullscreen"],
    div[data-testid="stImage"] [data-testid="stElementToolbar"] {
        background-color: #21262D !important;
        color: #F0F6FC !important;
        border: 1px solid #30363D !important;
        border-radius: 6px !important;
        opacity: 0.95 !important;
    }
    [data-testid="stElementToolbarButton"] svg,
    button[title="View fullscreen"] svg,
    button[aria-label="View fullscreen"] svg,
    [data-testid="stElementToolbar"] svg {
        fill: #F0F6FC !important;
        color: #F0F6FC !important;
    }
    /* Alert / Info Boxes in Dark Mode */
    [data-testid="stAlert"], div[data-testid="stAlert"], [data-testid="stAlert"] > div, [data-testid="stNotification"], div[role="alert"] {
        background-color: #161B22 !important;
        border: 1px solid #1E40AF !important;
        border-radius: 8px !important;
        color: #93C5FD !important;
    }
    [data-testid="stAlert"] *, div[data-testid="stAlert"] *, div[role="alert"] * {
        color: #93C5FD !important;
    }
    /* Toast Notifications in Dark Mode */
    [data-testid="stToast"],
    div[data-testid="stToast"],
    .stToast,
    div.stToast,
    [data-testid="stToastContainer"] > div {
        background-color: #161B22 !important;
        background: #161B22 !important;
        border: 1px solid #30363D !important;
        border-left: 4px solid #3B82F6 !important;
        border-radius: 8px !important;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.6) !important;
        color: #F0F6FC !important;
    }
    [data-testid="stToast"] *,
    div[data-testid="stToast"] *,
    .stToast *,
    [data-testid="stToastContainer"] *,
    [data-testid="stToast"] p,
    [data-testid="stToast"] span,
    [data-testid="stToast"] [data-testid="stMarkdownContainer"] p {
        color: #F0F6FC !important;
    }
    [data-testid="stToast"] button,
    .stToast button {
        background: transparent !important;
        border: none !important;
        color: #8B949E !important;
    }
    [data-testid="stToast"] button:hover *,
    .stToast button:hover * {
        color: #FFFFFF !important;
    }
    [data-testid="stToast"] svg {
        fill: #58A6FF !important;
        color: #58A6FF !important;
    }
    pre, code, [data-testid="stText"] {
        color: #F0F6FC !important;
        background-color: transparent !important;
    }
    /* Secondary & Regular Buttons */
    .stButton > button, button[kind="secondary"], button[data-testid*="secondary"], [data-testid="stPopover"] > button {
        background-color: #21262D !important;
        color: #F0F6FC !important;
        border: 1px solid #30363D !important;
        border-radius: 6px !important;
        font-weight: 500 !important;
    }
    .stButton > button *, button[kind="secondary"] *, button[data-testid*="secondary"] *, [data-testid="stPopover"] > button * {
        color: #F0F6FC !important;
    }
    .stButton > button:hover, button[kind="secondary"]:hover, [data-testid="stPopover"] > button:hover {
        background-color: #30363D !important;
        border-color: #8B949E !important;
        color: #FFFFFF !important;
    }
    .stButton > button:hover *, button[kind="secondary"]:hover *, [data-testid="stPopover"] > button:hover * {
        color: #FFFFFF !important;
    }
    /* Primary buttons */
    button[kind="primary"], button[data-testid*="primary"] {
        background-color: #2563EB !important;
        color: #FFFFFF !important;
        border: 1px solid #1D4ED8 !important;
    }
    button[kind="primary"] *, button[data-testid*="primary"] * {
        color: #FFFFFF !important;
        font-weight: 600 !important;
    }
    /* Download button */
    .stDownloadButton > button {
        background-color: #21262D !important;
        color: #F0F6FC !important;
        border: 1px solid #30363D !important;
    }
    .stDownloadButton > button * {
        color: #F0F6FC !important;
    }
    .stDownloadButton > button:hover {
        background-color: #30363D !important;
        color: #FFFFFF !important;
    }
    /* Popover */
    [data-testid="stPopoverBody"] {
        background-color: #161B22 !important;
        border: 1px solid #30363D !important;
        color: #F0F6FC !important;
    }
    hr {
        border-color: #30363D !important;
    }
    .field-card {
        background-color: #161B22 !important;
        border: 1px solid #30363D !important;
        border-radius: 6px;
        padding: 10px;
        margin-bottom: 8px;
        color: #E6EDF3 !important;
    }
    .pdf-frame {
        border: 1px solid #30363D;
        border-radius: 8px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.4);
        padding: 4px;
        background-color: #161B22;
    }
    ''' if is_dark else '''
    .stApp {
        background-color: #F8FAFC !important;
        color: #0F172A !important;
    }
    .app-title {
        font-size: 24px;
        font-weight: 700;
        color: #0F172A !important;
        margin-bottom: 2px;
    }
    .app-subtitle {
        font-size: 13px;
        color: #475569 !important;
        margin-bottom: 12px;
    }
    h1, h2, h3, h4, h5, h6, p, span, div {
        color: #0F172A;
    }
    .stMarkdown p, .stMarkdown span {
        color: #0F172A !important;
    }
    /* Labels & Captions */
    label, [data-testid="stWidgetLabel"] p {
        color: #0F172A !important;
        font-weight: 600 !important;
    }
    .stCaption, small {
        color: #475569 !important;
    }
    /* Inputs */
    div[data-baseweb="input"], div[data-baseweb="base-input"], .stTextInput > div > div {
        background-color: #FFFFFF !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 6px !important;
        color: #0F172A !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.04) !important;
    }
    input, textarea {
        background-color: transparent !important;
        color: #0F172A !important;
        caret-color: #0F172A !important;
    }
    input::placeholder {
        color: #94A3B8 !important;
    }
    /* File Uploader Dropzone & Uploaded File Items in Light Mode */
    [data-testid="stFileUploader"], [data-testid="stFileUploaderDropzone"], [data-testid="stFileUploader"] section {
        background-color: #FFFFFF !important;
        border: 2px dashed #94A3B8 !important;
        border-radius: 8px !important;
        color: #0F172A !important;
    }
    [data-testid="stFileUploaderDropzone"] *, [data-testid="stFileUploader"] section * {
        color: #0F172A !important;
    }
    /* Specific styling for the uploaded file pill/card in Light Mode */
    [data-testid="stFileUploaderDropzone"] [data-testid*="File"],
    [data-testid="stFileUploader"] [data-testid*="File"],
    [data-testid="stFileUploader"] section > div,
    [data-testid="stFileUploaderDropzone"] > div,
    [data-testid="stFileUploaderDropzone"] ul,
    [data-testid="stFileUploaderDropzone"] li,
    [data-testid="stFileUploaderDropzone"] div[target] {
        background-color: #F1F5F9 !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 6px !important;
        color: #0F172A !important;
    }
    [data-testid="stFileUploaderDropzone"] button, [data-testid="stFileUploader"] section button {
        background-color: #F1F5F9 !important;
        color: #0F172A !important;
        border: 1px solid #CBD5E1 !important;
    }
    [data-testid="stFileUploaderDropzone"] button *, [data-testid="stFileUploader"] svg {
        color: #0F172A !important;
        fill: #0F172A !important;
    }
    /* Fullscreen Button / Image Toolbar in Light Mode */
    [data-testid="stElementToolbar"],
    [data-testid="stElementToolbarButton"],
    button[title="View fullscreen"],
    button[aria-label="View fullscreen"],
    button[aria-label="Fullscreen"],
    div[data-testid="stImage"] [data-testid="stElementToolbar"] {
        background-color: #FFFFFF !important;
        color: #0F172A !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 6px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.15) !important;
        opacity: 0.95 !important;
    }
    [data-testid="stElementToolbarButton"] svg,
    button[title="View fullscreen"] svg,
    button[aria-label="View fullscreen"] svg,
    [data-testid="stElementToolbar"] svg {
        fill: #0F172A !important;
        color: #0F172A !important;
    }
    pre, code, [data-testid="stText"] {
        color: #0F172A !important;
        background-color: transparent !important;
    }
    /* Alert / Info Boxes in Light Mode */
    [data-testid="stAlert"], div[data-testid="stAlert"], [data-testid="stNotification"] {
        background-color: #EFF6FF !important;
        border: 1px solid #BFDBFE !important;
        border-radius: 8px !important;
        color: #1E40AF !important;
    }
    [data-testid="stAlert"] *, div[data-testid="stAlert"] * {
        color: #1E40AF !important;
    }
    /* Toast Notifications in Light Mode */
    [data-testid="stToast"],
    div[data-testid="stToast"],
    .stToast,
    div.stToast,
    [data-testid="stToastContainer"] > div {
        background-color: #FFFFFF !important;
        background: #FFFFFF !important;
        border: 1px solid #CBD5E1 !important;
        border-left: 4px solid #2563EB !important;
        border-radius: 8px !important;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.12) !important;
        color: #0F172A !important;
    }
    [data-testid="stToast"] *,
    div[data-testid="stToast"] *,
    .stToast *,
    [data-testid="stToastContainer"] *,
    [data-testid="stToast"] p,
    [data-testid="stToast"] span,
    [data-testid="stToast"] [data-testid="stMarkdownContainer"] p {
        color: #0F172A !important;
    }
    [data-testid="stToast"] button,
    .stToast button {
        background: transparent !important;
        border: none !important;
        color: #64748B !important;
    }
    [data-testid="stToast"] button:hover *,
    .stToast button:hover * {
        color: #0F172A !important;
    }
    [data-testid="stToast"] svg {
        fill: #2563EB !important;
        color: #2563EB !important;
    }
    /* Secondary & Regular Buttons */
    .stButton > button, button[kind="secondary"], button[data-testid*="secondary"], [data-testid="stPopover"] > button {
        background-color: #FFFFFF !important;
        color: #0F172A !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 6px !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
        font-weight: 500 !important;
    }
    .stButton > button *, button[kind="secondary"] *, button[data-testid*="secondary"] *, [data-testid="stPopover"] > button * {
        color: #0F172A !important;
        font-weight: 500 !important;
    }
    .stButton > button:hover, button[kind="secondary"]:hover, [data-testid="stPopover"] > button:hover {
        background-color: #F1F5F9 !important;
        border-color: #94A3B8 !important;
        color: #0F172A !important;
    }
    .stButton > button:hover *, button[kind="secondary"]:hover *, [data-testid="stPopover"] > button:hover * {
        color: #0F172A !important;
    }
    /* Primary buttons */
    button[kind="primary"], button[data-testid*="primary"] {
        background-color: #2563EB !important;
        color: #FFFFFF !important;
        border: 1px solid #1D4ED8 !important;
        box-shadow: 0 2px 4px rgba(37,99,235,0.2) !important;
    }
    button[kind="primary"] *, button[data-testid*="primary"] * {
        color: #FFFFFF !important;
        font-weight: 600 !important;
    }
    button[kind="primary"]:hover, button[data-testid*="primary"]:hover {
        background-color: #1D4ED8 !important;
    }
    /* Download button */
    .stDownloadButton > button {
        background-color: #FFFFFF !important;
        color: #0F172A !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 6px !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
    }
    .stDownloadButton > button * {
        color: #0F172A !important;
        font-weight: 500 !important;
    }
    .stDownloadButton > button:hover {
        background-color: #F1F5F9 !important;
        border-color: #94A3B8 !important;
        color: #0F172A !important;
    }
    /* Popover */
    [data-testid="stPopoverBody"] {
        background-color: #FFFFFF !important;
        border: 1px solid #CBD5E1 !important;
        color: #0F172A !important;
        box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1) !important;
    }
    hr {
        border-color: #E2E8F0 !important;
    }
    .field-card {
        background-color: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 6px;
        padding: 10px;
        margin-bottom: 8px;
        color: #0F172A !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.04) !important;
    }
    .pdf-frame {
        border: 1px solid #CBD5E1;
        border-radius: 8px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.08);
        padding: 4px;
        background-color: #FFFFFF;
    }
    '''}
</style>
"""
st.markdown(theme_css, unsafe_allow_html=True)


# Top Navigation Bar with Inline Theme Toggle (outside 3 dots)
c_title, c_nav, c_theme = st.columns([3.4, 2.2, 0.6], vertical_alignment="center")

with c_title:
    st.markdown("<div class='app-title'>📄 PDF Invoice Visual Editor & Manager</div>", unsafe_allow_html=True)
    st.markdown("<div class='app-subtitle'>Edit PDF text directly on the original document layout and manage saved invoices.</div>", unsafe_allow_html=True)

with c_nav:
    col_n1, col_n2 = st.columns(2)
    with col_n1:
        if st.button("📝 Visual PDF Editor", use_container_width=True, type="primary" if st.session_state.view_mode == "editor" else "secondary"):
            st.session_state.view_mode = "editor"
            st.rerun()
    with col_n2:
        if st.button("📁 Document Dashboard", use_container_width=True, type="primary" if st.session_state.view_mode == "dashboard" else "secondary"):
            st.session_state.view_mode = "dashboard"
            st.rerun()

with c_theme:
    toggle_icon = "☀️ Light" if is_dark else "🌙 Dark"
    tooltip = "Switch to Light Mode" if is_dark else "Switch to Dark Mode"
    if st.button(toggle_icon, help=tooltip, use_container_width=True):
        st.session_state.theme = "light" if is_dark else "dark"
        st.rerun()

st.markdown("---")


# ==============================================================================
# VIEW 1: VISUAL PDF EDITOR
# ==============================================================================
if st.session_state.view_mode == "editor":

    # Step 1: Document Management Header (Single Active Document Workflow)
    if st.session_state.current_pdf_bytes is None:
        st.markdown("##### 📤 Upload PDF Invoice:")
        uploaded_pdf = st.file_uploader(
            "Upload PDF Invoice:",
            type=["pdf"],
            help="Drop your PDF invoice here to edit its text while preserving the exact original layout.",
            label_visibility="collapsed"
        )
        if uploaded_pdf is not None:
            reset_document_state()
            new_bytes = uploaded_pdf.read()
            st.session_state.current_pdf_bytes = new_bytes
            st.session_state.current_pdf_name = uploaded_pdf.name
            st.session_state.current_page_idx = 0
            st.session_state.active_edits = []
            st.session_state.preview_bytes = None
            st.session_state["uploaded_via_uploader"] = True
            new_base = Path(uploaded_pdf.name).stem
            st.session_state["top_save_title_input"] = f"{new_base}_Edited"
            st.rerun()
    else:
        # A PDF is already active: Show active file badge & Safe New Upload / Close actions
        col_doc_info, col_doc_actions = st.columns([3.5, 2.5], vertical_alignment="center")
        with col_doc_info:
            doc_badge_color = "#93C5FD" if is_dark else "#1E40AF"
            doc_badge_bg = "#161B22" if is_dark else "#EFF6FF"
            doc_badge_border = "#30363D" if is_dark else "#BFDBFE"
            st.markdown(
                f"<div style='background-color:{doc_badge_bg}; border:1px solid {doc_badge_border}; "
                f"border-radius:6px; padding:8px 14px; font-size:14px; font-weight:600; color:{doc_badge_color};'>"
                f"📄 Active File: <b>{st.session_state.current_pdf_name}</b>"
                f"</div>",
                unsafe_allow_html=True
            )

        with col_doc_actions:
            c_btn_new, c_btn_disc = st.columns(2)
            with c_btn_new:
                with st.popover("➕ Upload New PDF", use_container_width=True):
                    st.markdown("##### ⚠️ New File Upload")
                    st.write(f"Pehle se **'{st.session_state.current_pdf_name}'** open hai. Aap kya karna chahte hain?")
                    
                    if st.button("💾 Save & Open New", type="primary", use_container_width=True):
                        cur_save_title = st.session_state.get("top_save_title_input", f"{Path(st.session_state.current_pdf_name).stem}_Edited")
                        clean_fn = f"{cur_save_title.strip().replace(' ', '_')}.pdf"
                        final_bytes = st.session_state.preview_bytes or st.session_state.current_pdf_bytes
                        final_p = SAVED_DIR / clean_fn
                        with open(final_p, "wb") as f:
                            f.write(final_bytes)
                        save_document(
                            title=cur_save_title,
                            filename=clean_fn,
                            file_path=str(final_p),
                            original_filename=st.session_state.current_pdf_name,
                            page_count=get_pdf_page_count(final_bytes),
                            file_size_kb=round(len(final_bytes) / 1024.0, 2)
                        )
                        st.toast(f"Saved '{clean_fn}' to Dashboard!")
                        reset_document_state()
                        st.rerun()

                    if st.button("🗑️ Discard & Open New", use_container_width=True):
                        reset_document_state()
                        st.toast("Previous PDF discarded. Ab new PDF upload karein.")
                        st.rerun()

            with c_btn_disc:
                if st.button("❌ Close File", use_container_width=True, help="File band kar k upload screen par wapis jayein"):
                    reset_document_state()
                    st.rerun()

    # Step 2: Main Editor Canvas & Controls
    if st.session_state.current_pdf_bytes is not None:
        source_bytes = st.session_state.preview_bytes if st.session_state.preview_bytes is not None else st.session_state.current_pdf_bytes
        total_pages = get_pdf_page_count(source_bytes)

        # TOP BAR: Save As & Export (Immediately visible without scrolling)
        orig_base = Path(st.session_state.current_pdf_name).stem
        default_save_name = f"{orig_base}_Edited"
        final_bytes_to_save = st.session_state.preview_bytes or st.session_state.current_pdf_bytes

        with st.container():
            st.markdown("#### 💾 Save As & Export")
            col_s1, col_s2, col_s3 = st.columns([3.5, 2, 2], vertical_alignment="bottom")
            with col_s1:
                custom_save_title = st.text_input("Save Document As (Title/Name):", value=default_save_name, key="top_save_title_input")
            
            clean_filename = f"{custom_save_title.strip().replace(' ', '_')}.pdf"

            with col_s2:
                if st.button("💾 Save to Dashboard", type="primary", use_container_width=True, key="top_save_to_dash_btn"):
                    final_path = SAVED_DIR / clean_filename
                    with open(final_path, "wb") as f:
                        f.write(final_bytes_to_save)

                    size_kb = round(len(final_bytes_to_save) / 1024.0, 2)
                    doc_id = save_document(
                        title=custom_save_title,
                        filename=clean_filename,
                        file_path=str(final_path),
                        original_filename=st.session_state.current_pdf_name,
                        page_count=total_pages,
                        file_size_kb=size_kb
                    )
                    saved_title_copy = clean_filename
                    reset_document_state()
                    st.toast(f"✓ '{saved_title_copy}' Dashboard me save ho gaya! Editor reset ho gaya hai.")
                    st.rerun()

            with col_s3:
                st.download_button(
                    label="📥 Download PDF Now",
                    data=final_bytes_to_save,
                    file_name=clean_filename,
                    mime="application/pdf",
                    use_container_width=True,
                    key="top_dl_pdf_btn"
                )

        st.markdown("---")

        # Multi-page pagination bar
        col_p1, col_p2, col_p3, col_p4 = st.columns([1, 1, 2, 2], vertical_alignment="center")
        with col_p1:
            if st.button("◀ Previous Page", disabled=(st.session_state.current_page_idx <= 0)):
                st.session_state.current_page_idx -= 1
                st.rerun()
        with col_p2:
            if st.button("Next Page ▶", disabled=(st.session_state.current_page_idx >= total_pages - 1)):
                st.session_state.current_page_idx += 1
                st.rerun()
        with col_p3:
            p_bg = "#161B22" if is_dark else "#EFF6FF"
            p_border = "#30363D" if is_dark else "#BFDBFE"
            p_txt = "#93C5FD" if is_dark else "#1E40AF"
            st.markdown(
                f"<div style='background-color:{p_bg}; border:1px solid {p_border}; "
                f"border-radius:6px; padding:7px 12px; text-align:center; font-size:13px; font-weight:500; color:{p_txt};'>"
                f"📄 Page <b>{st.session_state.current_page_idx + 1}</b> of <b>{total_pages}</b> &nbsp;•&nbsp; <span>{st.session_state.current_pdf_name}</span>"
                f"</div>",
                unsafe_allow_html=True
            )
        with col_p4:
            if st.session_state.preview_bytes is not None:
                if st.button("🔄 Reset Edits to Original"):
                    st.session_state.preview_bytes = None
                    st.session_state.active_edits = []
                    st.rerun()

        # Render Page Image
        curr_page = st.session_state.current_page_idx
        img_page, page_w, page_h = render_pdf_page_image(source_bytes, page_number=curr_page, dpi=160)
        detected_blocks = extract_page_text_blocks(st.session_state.current_pdf_bytes, page_number=curr_page)

        # Prepare page image base64 for direct interactive visual canvas
        buffered = io.BytesIO()
        img_page.save(buffered, format="PNG")
        img_b64 = base64.b64encode(buffered.getvalue()).decode()
        doc_token = "".join(c for c in (st.session_state.current_pdf_name or "doc") if c.isalnum() or c == '_')

        # Direct In-Place Visual PDF Canvas Editor
        if detected_blocks:
            canvas_result = canvas_editor_component(
                image_base64=img_b64,
                blocks=detected_blocks,
                page_width=page_w,
                page_height=page_h,
                theme_mode="dark" if is_dark else "light",
                key=f"canvas_editor_p{curr_page}_{doc_token}_{len(st.session_state.active_edits)}"
            )

            if canvas_result and isinstance(canvas_result, dict) and canvas_result.get("action") == "apply":
                canvas_edits = canvas_result.get("edits", [])
                if canvas_edits:
                    processed_edits = []
                    for ed in canvas_edits:
                        orig_text = ed.get("original_text", "")
                        new_val = ed.get("new_text", "").strip()
                        if orig_text.startswith("_") and not new_val.startswith("_"):
                            lead = orig_text[:len(orig_text) - len(orig_text.lstrip("_"))]
                            trail = orig_text[len(orig_text.rstrip("_")):]
                            new_val = f"{lead}{new_val}{trail}"
                        elif orig_text.startswith("-") and not new_val.startswith("-"):
                            lead = orig_text[:len(orig_text) - len(orig_text.lstrip("-"))]
                            trail = orig_text[len(orig_text.rstrip("-")):]
                            new_val = f"{lead}{new_val}{trail}"
                        
                        ed["new_text"] = new_val
                        ed["page"] = curr_page
                        processed_edits.append(ed)

                    temp_out = DATA_DIR / f"temp_canvas_edit_{int(time.time())}.pdf"
                    apply_edits_and_export(
                        source_pdf=source_bytes,
                        edits=processed_edits,
                        output_path=temp_out
                    )
                    st.session_state.preview_bytes = temp_out.read_bytes()
                    st.session_state.active_edits.extend(processed_edits)
                    if temp_out.exists():
                        temp_out.unlink()
                    st.toast(f"✓ {len(processed_edits)} edits applied directly to PDF!")
                    st.rerun()

            # Optional Collapsible List View
            with st.expander("📋 Optional: Search & Edit Fields in Quick Table List"):
                with st.form("form_detected_edits"):
                    page_edits_input = []
                    for blk in detected_blocks:
                        orig_text = blk["text"]
                        blk_id = blk["id"]
                        c_f1, c_f2 = st.columns([1, 2])
                        with c_f1:
                            font_label = blk.get("font_display", f"{blk['font_size']}pt")
                            text_display = orig_text[:32] + ("..." if len(orig_text) > 32 else "")
                            f_txt_color = "#F0F6FC" if is_dark else "#0F172A"
                            f_cap_color = "#8B949E" if is_dark else "#64748B"
                            st.markdown(
                                f"<div style='line-height:1.25; padding:2px 0;'>"
                                f"<div style='font-size:11px; color:{f_cap_color}; margin-bottom:2px;'>🔒 {font_label} • ({blk['x0']:.0f}, {blk['y0']:.0f})</div>"
                                f"<div style='font-size:13px; font-weight:600; color:{f_txt_color}; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;'>{text_display}</div>"
                                f"</div>",
                                unsafe_allow_html=True
                            )
                        with c_f2:
                            val = st.text_input(
                                label=f"Edit {blk_id}",
                                value=orig_text,
                                key=f"input_{doc_token}_p{curr_page}_{blk_id}",
                                label_visibility="collapsed"
                            )
                            if val != orig_text:
                                val_to_save = val.strip()
                                if orig_text.startswith("_") and not val_to_save.startswith("_"):
                                    lead = orig_text[:len(orig_text) - len(orig_text.lstrip("_"))]
                                    trail = orig_text[len(orig_text.rstrip("_")):]
                                    val_to_save = f"{lead}{val_to_save}{trail}"
                                elif orig_text.startswith("-") and not val_to_save.startswith("-"):
                                    lead = orig_text[:len(orig_text) - len(orig_text.lstrip("-"))]
                                    trail = orig_text[len(orig_text.rstrip("-")):]
                                    val_to_save = f"{lead}{val_to_save}{trail}"

                                page_edits_input.append({
                                    "page": curr_page,
                                    "type": "replace",
                                    "rect": [blk["x0"], blk["y0"], blk["x1"], blk["y1"]],
                                    "new_text": val_to_save,
                                    "original_text": orig_text,
                                    "font_size": blk["font_size"],
                                    "font_name": blk.get("font_name", "helv"),
                                    "font_color": blk.get("font_color", (0.0, 0.0, 0.0)),
                                    "baseline_y": blk.get("baseline_y")
                                })

                    submit_list = st.form_submit_button("⚡ Apply List Changes to PDF", type="secondary")
                    if submit_list and page_edits_input:
                        temp_out = DATA_DIR / f"temp_preview_{int(time.time())}.pdf"
                        apply_edits_and_export(
                            source_pdf=source_bytes,
                            edits=page_edits_input,
                            output_path=temp_out
                        )
                        st.session_state.preview_bytes = temp_out.read_bytes()
                        st.session_state.active_edits.extend(page_edits_input)
                        if temp_out.exists():
                            temp_out.unlink()
                        st.toast(f"✓ {len(page_edits_input)} edits applied!")
                        st.rerun()
        else:
            st.info("ℹ️ No editable vector text elements were detected on this page.")


    else:
        st.info("👉 Upload a PDF invoice above to begin visual in-place editing.")


# ==============================================================================
# VIEW 2: SAVED INVOICES DASHBOARD (CRUD)
# ==============================================================================
elif st.session_state.view_mode == "dashboard":
    st.markdown("### 📁 Saved Invoices Dashboard")
    st.markdown("Manage all previously edited and exported PDF invoices. Full CRUD operations (Preview, Download, Re-edit, Delete).")

    # Search Bar
    search_q = st.text_input("Search Invoices (Title or Filename):", placeholder="e.g. Faire or Apex...")
    saved_docs = list_documents(search_query=search_q)

    if not saved_docs:
        st.info("No saved documents found in database. Edit and save an invoice in the Visual PDF Editor to see it here!")
    else:
        st.write(f"Found **{len(saved_docs)}** saved document(s):")

        # Saved Documents List - Single Clean Line per Document
        for doc in saved_docs:
            doc_id = doc["id"]
            doc_title = doc["title"]
            doc_file = doc["filename"]
            doc_path = Path(doc["file_path"])
            # Extract date only (YYYY-MM-DD), removing time
            created_raw = str(doc.get("created_at", ""))
            doc_date = created_raw.split(" ")[0] if " " in created_raw else created_raw

            title_color = "#0F172A" if not is_dark else "#F0F6FC"
            date_color = "#475569" if not is_dark else "#8B949E"

            with st.container():
                c_info, c_view, c_edit, c_dl, c_del = st.columns([4.0, 1.1, 1.1, 1.3, 1.1], vertical_alignment="center")

                # PDF Name and Date only
                with c_info:
                    st.markdown(
                        f"<div style='font-size:15px; font-weight:600; padding:6px 0; color:{title_color};'>"
                        f"📄 {doc_title} <span style='font-size:13px; font-weight:400; color:{date_color}; margin-left:8px;'>({doc_date})</span>"
                        f"</div>",
                        unsafe_allow_html=True
                    )

                # 1. View / Preview Popover
                with c_view:
                    with st.popover("👁️ View", use_container_width=True):
                        if doc_path.exists():
                            p_img, _, _ = render_pdf_page_image(doc_path, page_number=0, dpi=140)
                            st.image(p_img, caption=f"{doc_title} (Page 1)", use_container_width=True)
                        else:
                            st.error("File not found on disk.")

                # 2. Edit
                with c_edit:
                    if st.button("✏️ Edit", key=f"edit_{doc_id}", use_container_width=True):
                        if doc_path.exists():
                            reset_document_state()
                            st.session_state.current_pdf_bytes = doc_path.read_bytes()
                            st.session_state.current_pdf_name = doc_file
                            st.session_state.current_page_idx = 0
                            st.session_state.active_edits = []
                            st.session_state.preview_bytes = None
                            st.session_state["uploaded_via_uploader"] = False
                            st.session_state["top_save_title_input"] = f"{Path(doc_file).stem}_Edited"
                            st.session_state.view_mode = "editor"
                            st.rerun()

                # 3. Download
                with c_dl:
                    if doc_path.exists():
                        st.download_button(
                            label="📥 Download",
                            data=doc_path.read_bytes(),
                            file_name=doc_file,
                            mime="application/pdf",
                            key=f"dl_dash_{doc_id}",
                            use_container_width=True
                        )
                    else:
                        st.button("Missing", disabled=True, key=f"btn_miss_{doc_id}", use_container_width=True)

                # 4. Delete
                with c_del:
                    if st.button("🗑️ Delete", key=f"del_{doc_id}", type="secondary", use_container_width=True):
                        delete_document(doc_id)
                        st.toast(f"Deleted '{doc_title}'")
                        st.rerun()

                st.divider()
