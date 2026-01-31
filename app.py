import streamlit as st
from streamlit_drawable_canvas import st_canvas
from pdf2image import convert_from_bytes
from PIL import Image, ImageDraw
import pytesseract
from PyPDF2 import PdfReader, PdfWriter
from docx import Document
from pdf2docx import Converter
from fpdf import FPDF # Word to PDF ke liye
import io
import tempfile
import os

# =====================================================
# CONFIG
# =====================================================
st.set_page_config("All-in-One Editor", layout="wide")
st.title("📄 All-in-One: PDF & Word Editor")

MAX_PAGES = 15
DPI = 200
CANVAS_WIDTH = 800

# =====================================================
# UTILITIES
# =====================================================
def word_to_pdf_buffer(word_file):
    """Word file ko PDF bytes me badalta hai (Linux Safe)"""
    doc = Document(word_file)
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    for p in doc.paragraphs:
        safe_text = p.text.encode('latin-1', 'replace').decode('latin-1')
        if safe_text.strip():
            pdf.multi_cell(0, 10, safe_text)
            pdf.ln(1)
    return bytes(pdf.output())

def pdf_to_images(file_bytes):
    try:
        return convert_from_bytes(file_bytes, dpi=DPI)
    except Exception as e:
        st.error("Error: Poppler Utils missing.")
        st.stop()

def resize(img):
    ratio = CANVAS_WIDTH / img.width
    return img.resize((CANVAS_WIDTH, int(img.height * ratio)))

def save_pdf_from_images(image_list):
    if not image_list: return None
    buf = io.BytesIO()
    rgb_images = [img.convert("RGB") for img in image_list]
    rgb_images[0].save(buf, format="PDF", save_all=True, append_images=rgb_images[1:])
    return buf.getvalue()

# =====================================================
# SESSION STATE INIT
# =====================================================
if "file_key" not in st.session_state:
    st.session_state.file_key = None
if "pages" not in st.session_state:
    st.session_state.pages = []

# =====================================================
# SIDEBAR
# =====================================================
st.sidebar.markdown("## 🛠️ Menu")
tool = st.sidebar.radio("Select Tool", ["📝 Magic Editor (PDF/Word)", "Word ↔ PDF", "Image → PDF"])

# =====================================================
# 1. MAGIC EDITOR (PDF & WORD SUPPORT)
# =====================================================
if tool == "📝 Magic Editor (PDF/Word)":
    st.header("📝 Smart Editor (Whitener & Type)")
    
    st.info("💡 **Kaise Edit Karein?** \n1. **Whitener** tool se purana text mitayein (chupayein). \n2. **Text** tool se uske upar naya likhein.")

    # Accept PDF AND Word
    uploaded = st.file_uploader("Upload File (PDF or Word)", type=["pdf", "docx"])

    if uploaded:
        # Load Logic
        if st.session_state.file_key != uploaded.name:
            st.session_state.file_key = uploaded.name
            
            with st.spinner("Processing file..."):
                if uploaded.name.endswith(".pdf"):
                    # Direct PDF
                    file_bytes = uploaded.read()
                else:
                    # Convert Word to PDF first
                    file_bytes = word_to_pdf_buffer(uploaded)
                    st.toast("Word file converted to PDF for editing!", icon="ℹ️")

                st.session_state.pages = pdf_to_images(file_bytes)
        
        pages = st.session_state.pages

        if len(pages) > 0:
            # Page Selector
            col_nav1, col_nav2 = st.columns([1, 3])
            with col_nav1:
                pg_idx = st.number_input("Page:", 1, len(pages), 1) - 1
            
            # Editor Tools
            st.markdown("### 🎨 Toolbox")
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                # Custom Names for tools
                tool_select = st.selectbox("Tool", ["Hand (Move)", "⬜ Whitener (Eraser)", "🔤 Text (Type)", "🖌️ Draw"])
            with c2:
                stroke_width = st.slider("Size", 1, 30, 10)
            with c3:
                stroke_color = st.color_picker("Color", "#000000")
            
            # Tool Logic Mapping
            drawing_mode = "transform"
            fill_color = "rgba(0,0,0,0)" # Transparent default
            
            if tool_select == "⬜ Whitener (Eraser)":
                drawing_mode = "rect"
                stroke_color = "#FFFFFF" # White Border
                fill_color = "#FFFFFF"   # White Fill
                st.caption("👉 Box banakar text chupayein")
                
            elif tool_select == "🔤 Text (Type)":
                drawing_mode = "text"
                st.caption("👉 Click karke likhein")
                
            elif tool_select == "🖌️ Draw":
                drawing_mode = "freedraw"

            # Canvas Setup
            page_img = pages[pg_idx].convert("RGB")
            canvas_bg = resize(page_img)
            
            # Unique Key for Canvas
            canvas_key = f"canvas_{uploaded.name}_{pg_idx}_{tool_select}"

            canvas = st_canvas(
                fill_color=fill_color,
                stroke_width=stroke_width,
                stroke_color=stroke_color,
                background_image=canvas_bg,
                height=canvas_bg.height,
                width=canvas_bg.width,
                drawing_mode=drawing_mode,
                key=canvas_key,
                display_toolbar=True
            )

            # SAVE LOGIC
            if st.button("💾 Save Page Changes"):
                if canvas.image_data is not None:
                    edited = Image.fromarray(canvas.image_data.astype("uint8")).convert("RGBA")
                    bg = page_img.copy().convert("RGBA")
                    edited = edited.resize(bg.size)
                    final = Image.alpha_composite(bg, edited).convert("RGB")
                    
                    st.session_state.pages[pg_idx] = final
                    st.success("Page Saved! (Ab 'Download PDF' dabayein)")
                    st.rerun()

            st.markdown("---")
            if st.button("📥 Download Final PDF"):
                final_pdf = save_pdf_from_images(st.session_state.pages)
                st.download_button("Click to Download", final_pdf, "edited_document.pdf")

# =====================================================
# 2. WORD <-> PDF CONVERTER
# =====================================================
elif tool == "Word ↔ PDF":
    st.header("🔄 Format Converter")
    tab1, tab2 = st.tabs(["PDF → Word", "Word → PDF"])
    
    with tab1:
        f = st.file_uploader("Upload PDF", type=["pdf"], key="p2w")
        if f and st.button("Convert to Word"):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(f.read())
                p_path = tmp.name
            d_path = p_path.replace(".pdf", ".docx")
            try:
                cv = Converter(p_path)
                cv.convert(d_path)
                cv.close()
                with open(d_path, "rb") as o:
                    st.download_button("Download Word", o.read(), "converted.docx")
            except Exception as e: st.error(e)

    with tab2:
        f = st.file_uploader("Upload Word", type=["docx"], key="w2p")
        if f and st.button("Convert to PDF"):
            try:
                pdf_bytes = word_to_pdf_buffer(f)
                st.download_button("Download PDF", pdf_bytes, "converted.pdf")
            except Exception as e: st.error(e)

# =====================================================
# 3. IMAGE TO PDF
# =====================================================
elif tool == "Image → PDF":
    st.header("🖼️ Images to PDF")
    imgs = st.file_uploader("Select Images", type=["png","jpg"], accept_multiple_files=True)
    if imgs and st.button("Convert"):
        try:
            pil_imgs = [Image.open(i).convert("RGB") for i in imgs]
            buf = io.BytesIO()
            pil_imgs[0].save(buf, format="PDF", save_all=True, append_images=pil_imgs[1:])
            st.download_button("Download PDF", buf.getvalue(), "images.pdf")
        except Exception as e: st.error(e)
