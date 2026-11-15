import os
import sys
import time
from pathlib import Path
from datetime import datetime

import streamlit as st
import io
import base64
import streamlit.components.v1 as components

# Add current workspace to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

CANVAS_DIR = Path(__file__).resolve().parent / "canvas_component"
canvas_editor_component = components.declare_component("canvas_editor", path=str(CANVAS_DIR))

from config import DATA_DIR
import importlib
import pdf_engine
importlib.reload(pdf_engine)
from pdf_engine import (
    get_pdf_page_count,
    render_pdf_page_image,
    extract_page_text_blocks,
    apply_edits_and_export,
    detect_end_table_rows,
    duplicate_table_row_and_shift
)

# Page Setup: Clean Full-Width View without Sidebar Clutter
st.set_page_config(
    page_title="PDF Invoice Visual Editor",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="collapsed"
)


def reset_document_state():
    """Completely resets active document and purges all cached input fields."""
    st.session_state.current_pdf_bytes = None
    st.session_state.original_pdf_bytes = None
    st.session_state.current_pdf_name = None
    st.session_state.current_page_idx = 0
    st.session_state.active_edits = []
    st.session_state.preview_bytes = None
    st.session_state["uploaded_via_uploader"] = False

    # Purge any cached input keys
    keys_to_clear = [k for k in list(st.session_state.keys()) if k.startswith("input_")]
    for k in keys_to_clear:
        del st.session_state[k]


# Session State Initialization
if "current_pdf_bytes" not in st.session_state:
    st.session_state.current_pdf_bytes = None
if "original_pdf_bytes" not in st.session_state:
    st.session_state.original_pdf_bytes = None
if "current_pdf_name" not in st.session_state:
    st.session_state.current_pdf_name = None
if "current_page_idx" not in st.session_state:
    st.session_state.current_page_idx = 0
if "active_edits" not in st.session_state:
    st.session_state.active_edits = []
if "preview_bytes" not in st.session_state:
    st.session_state.preview_bytes = None

# Custom Styling: Clean, Modern Light Theme (No Dark Mode)
theme_css = """
<style>
    /* Complete Removal of 3 dots menu, Deploy button, and Header chrome */
    #MainMenu { visibility: hidden !important; display: none !important; }
    header { visibility: hidden !important; display: none !important; height: 0 !important; }
    footer { visibility: hidden !important; display: none !important; }
    .stAppDeployButton { display: none !important; }
    [data-testid="stAppDeployButton"] { display: none !important; }
    [data-testid="stToolbar"] { display: none !important; visibility: hidden !important; }
    [data-testid="stDecoration"] { display: none !important; }
    [data-testid="stStatusWidget"] { display: none !important; }
    [data-testid="collapsedControl"] { display: none !important; }
    section[data-testid="stSidebar"] { display: none !important; }

    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 2rem !important;
        max-width: 1050px !important;
    }

    .stApp {
        background-color: #F8FAFC !important;
        color: #0F172A !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
    }
    .app-title {
        font-size: 26px;
        font-weight: 700;
        color: #0F172A !important;
        margin-bottom: 3px;
    }
    .app-subtitle {
        font-size: 14px;
        color: #64748B !important;
        margin-bottom: 14px;
    }
    h1, h2, h3, h4, h5, h6, p, span, div {
        color: #0F172A;
    }
    .stMarkdown p, .stMarkdown span {
        color: #0F172A !important;
    }

    /* File Uploader Clean Light Style */
    [data-testid="stFileUploader"], [data-testid="stFileUploaderDropzone"], [data-testid="stFileUploader"] section {
        background-color: #FFFFFF !important;
        border: 2px dashed #CBD5E1 !important;
        border-radius: 10px !important;
        color: #0F172A !important;
    }
    [data-testid="stFileUploaderDropzone"]:hover {
        border-color: #2563EB !important;
        background-color: #F0F7FF !important;
    }
    [data-testid="stFileUploaderDropzone"] *, [data-testid="stFileUploader"] section * {
        color: #0F172A !important;
    }

    /* Buttons */
    .stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] {
        background: #2563EB !important;
        color: #FFFFFF !important;
        border: none !important;
        font-weight: 600 !important;
        border-radius: 6px !important;
        transition: all 0.15s ease !important;
    }
    .stButton > button[kind="primary"]:hover, .stDownloadButton > button[kind="primary"]:hover {
        background: #1D4ED8 !important;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3) !important;
    }
    .stButton > button[kind="secondary"] {
        background: #FFFFFF !important;
        color: #475569 !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 6px !important;
    }
    .stButton > button[kind="secondary"]:hover {
        background: #F1F5F9 !important;
        border-color: #94A3B8 !important;
        color: #0F172A !important;
    }
</style>
"""
st.markdown(theme_css, unsafe_allow_html=True)

# Top Header
st.markdown("<div class='app-title'>📄 PDF Invoice Visual Editor</div>", unsafe_allow_html=True)
st.markdown("<div class='app-subtitle'>Click any text directly on the document to edit, apply changes, and download your edited PDF.</div>", unsafe_allow_html=True)
st.markdown("---")


# ==============================================================================
# SINGLE-SCREEN VISUAL WORKFLOW
# ==============================================================================

# Screen State 1: Upload Dropzone (When no PDF is active)
if st.session_state.current_pdf_bytes is None:
    st.markdown("##### 📤 Upload PDF Invoice:")
    uploaded_pdf = st.file_uploader(
        "Upload PDF Invoice:",
        type=["pdf"],
        help="Drop your PDF invoice here to edit its text while preserving the exact original layout and fonts.",
        label_visibility="collapsed"
    )
    if uploaded_pdf is not None:
        reset_document_state()
        new_bytes = uploaded_pdf.read()
        st.session_state.current_pdf_bytes = new_bytes
        st.session_state.original_pdf_bytes = new_bytes
        st.session_state.current_pdf_name = uploaded_pdf.name
        st.session_state.current_page_idx = 0
        st.session_state.active_edits = []
        st.session_state.preview_bytes = None
        st.session_state["uploaded_via_uploader"] = True
        st.rerun()

# Screen State 2: Direct Visual Editor Canvas & Download
else:
    source_bytes = st.session_state.preview_bytes if st.session_state.preview_bytes is not None else st.session_state.current_pdf_bytes
    total_pages = get_pdf_page_count(source_bytes)

    orig_base = Path(st.session_state.current_pdf_name).stem
    download_filename = f"{orig_base}_Edited.pdf"
    final_bytes_to_export = st.session_state.preview_bytes or st.session_state.current_pdf_bytes

    # Action Bar: Direct Download with Automatic Reset upon Download
    with st.container():
        col_info, col_reset, col_dl = st.columns([3.8, 1.8, 1.6], vertical_alignment="center")
        with col_info:
            if st.session_state.preview_bytes is not None:
                st.markdown(
                    f"<div style='font-size:14px; color:#10B981; font-weight:600; padding:6px 0;'>"
                    f"✓ Edits applied ({len(st.session_state.active_edits)} change(s)). Ready to download!"
                    f"</div>",
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f"<div style='font-size:13px; color:#64748B; padding:6px 0;'>"
                    f"📄 Active File: <b>{st.session_state.current_pdf_name}</b> • Click any text below to edit in-place."
                    f"</div>",
                    unsafe_allow_html=True
                )

        with col_reset:
            has_row_mods = (st.session_state.get("original_pdf_bytes") is not None and 
                            st.session_state.current_pdf_bytes != st.session_state.original_pdf_bytes)
            if has_row_mods:
                col_r1, col_r2 = st.columns(2)
                with col_r1:
                    if st.button("🔄 Reset", use_container_width=True, help="Revert to clean original document without extra rows"):
                        st.session_state.current_pdf_bytes = st.session_state.original_pdf_bytes
                        st.session_state.preview_bytes = None
                        st.session_state.active_edits = []
                        st.rerun()
                with col_r2:
                    if st.button("❌ Close", use_container_width=True, help="Discard file and return to upload screen"):
                        reset_document_state()
                        st.rerun()
            else:
                if st.button("❌ Close File", use_container_width=True, help="Discard file and return to upload screen"):
                    reset_document_state()
                    st.rerun()

        with col_dl:
            # When clicked, the file downloads and state auto-resets back to upload screen!
            st.download_button(
                label="📥 Download PDF",
                data=final_bytes_to_export,
                file_name=download_filename,
                mime="application/pdf",
                type="primary",
                use_container_width=True,
                key="top_dl_pdf_btn",
                on_click=reset_document_state
            )

    st.markdown("---")

    # Multi-page pagination bar (if multi-page PDF)
    if total_pages > 1 or st.session_state.preview_bytes is not None:
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
            st.markdown(
                f"<div style='background-color:#F1F5F9; border:1px solid #CBD5E1; "
                f"border-radius:6px; padding:7px 12px; text-align:center; font-size:13px; font-weight:500; color:#1E40AF;'>"
                f"📄 Page <b>{st.session_state.current_page_idx + 1}</b> of <b>{total_pages}</b>"
                f"</div>",
                unsafe_allow_html=True
            )
        with col_p4:
            if st.session_state.preview_bytes is not None:
                if st.button("🔄 Reset to Original PDF", use_container_width=True):
                    st.session_state.preview_bytes = None
                    st.session_state.active_edits = []
                    st.rerun()

    # Render Active Page Image
    curr_page = st.session_state.current_page_idx
    img_page, page_w, page_h = render_pdf_page_image(source_bytes, page_number=curr_page, dpi=160)
    detected_blocks = extract_page_text_blocks(source_bytes, page_number=curr_page)
    end_table_rows = detect_end_table_rows(source_bytes, page_number=curr_page)

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
            end_rows=end_table_rows,
            page_width=page_w,
            page_height=page_h,
            theme_mode="light",
            key=f"canvas_editor_p{curr_page}_{doc_token}_{len(st.session_state.active_edits)}_{len(detected_blocks)}"
        )

        if canvas_result and isinstance(canvas_result, dict):
            act = canvas_result.get("action")

            # 1. ADD ROW: Duplicate row and shift all content below down
            if act == "add_row":
                row_data = canvas_result.get("row_data", {})
                temp_out = DATA_DIR / f"temp_add_row_{int(time.time() * 1000)}.pdf"
                try:
                    duplicate_table_row_and_shift(
                        source_pdf=source_bytes,
                        page_number=curr_page,
                        row_data=row_data,
                        output_path=temp_out
                    )
                    if temp_out.exists():
                        new_pdf_bytes = temp_out.read_bytes()
                        st.session_state.current_pdf_bytes = new_pdf_bytes
                        st.session_state.preview_bytes = None
                        st.session_state.active_edits = []
                        st.toast("✓ New row added successfully! You can now click and edit the new cells.")
                finally:
                    if temp_out.exists():
                        try:
                            temp_out.unlink()
                        except Exception:
                            pass
                st.rerun()

            # 2. APPLY EDITS: Save text edits to PDF
            elif act == "apply":
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
    else:
        st.info("ℹ️ No editable vector text elements were detected on this page.")
