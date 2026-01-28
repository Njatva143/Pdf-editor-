import streamlit as st
from streamlit_drawable_canvas import st_canvas
from pdf2image import convert_from_bytes
from pdf2docx import Converter
from fpdf import FPDF
from PIL import Image
from docx import Document
import io
import os
import numpy as np

# ----------------- MAGIC PATCH -----------------
try:
    import streamlit.elements.image
    from streamlit.elements.utils import image_to_url
    if not hasattr(streamlit.elements.image, "image_to_url"):
        streamlit.elements.image.image_to_url = image_to_url
except Exception:
    pass
# -----------------------------------------------

# --- PAGE CONFIG ---
st.set_page_config(page_title="PDF Editor & Converter", layout="wide")
st.title("📄 Professional PDF Tool")

# --- HELPER: UNICODE TO KRUTI DEV ---
def convert_to_kruti(text):
    text = text.replace("त्र", "=k").replace("ज्ञ", "%").replace("श्र", "J")
    chars = list(text)
    i = 0
    while i < len(chars):
        if chars[i] == 'ि' and i > 0:
            prev = chars[i-1]
            chars[i-1] = 'f'
            chars[i] = prev
        i += 1
    text = "".join(chars)
    mapping = {
        'ा': 'k', 'ी': 'h', 'ु': 'q', 'ू': 'w', 'ृ': '`', 'े': 's', 'ै': 'S',
        'ो': 'ks', 'ौ': 'kS', 'ं': 'a', 'ँ': '¡', 'ः': '%', '्': 'd', '़': '+',
        'क': 'd', 'ख': '[', 'ग': 'x', 'घ': '?', 'च': 'p', 'छ': 'N', 'ज': 't', 'झ': '>',
        'ट': 'V', 'ठ': 'B', 'ड': 'M', 'ढ': '<', 'ण': '.', 'त': 'r', 'थ': 'F', 'द': 'n',
        'ध': 'è', 'न': 'u', 'प': 'i', 'फ': 'Q', 'ब': 'c', 'भ': 'H', 'म': 'e', 'य': ';',
        'र': 'j', 'ल': 'y', 'व': 'b', 'श': 'M', 'ष': 'k', 'स': 'l', 'ह': 'v',
        '०': '0', '१': '1', '२': '2', '३': '3', '४': '4', '५': '5', '६': '6', '७': '7', '८': '8', '९': '9',
        '.': 'A', ',': ',', '-': '-', '(': '¼', ')': '½'
    }
    return "".join(mapping.get(c, c) for c in text)

# --- MENU ---
st.sidebar.title("🚀 Main Menu")
app_mode = st.sidebar.radio("Go to:", ["✏️ PDF Direct Editor", "🔄 Universal Converter"])

# ==================================================
# 1️⃣ PDF DIRECT EDITOR
# ==================================================
if app_mode == "✏️ PDF Direct Editor":
    st.header("✏️ PDF Direct Editor")

    uploaded_file = st.file_uploader("Upload PDF/Image", type=["pdf", "jpg", "png"], key="canvas_upl")

    col1, col2 = st.columns(2)
    with col1:
        drawing_mode = st.selectbox("Tool:", ("rect", "text", "transform"))
    with col2:
        stroke_width = st.slider("Size", 1, 50, 15)

    stroke_color = "#000000"
    if drawing_mode == "text":
        stroke_color = st.color_picker("Color", "#000000")
    elif drawing_mode == "rect":
        stroke_color = "#FFFFFF"

    canvas_result = None

    if uploaded_file:
        image = None
        if uploaded_file.name.lower().endswith(".pdf"):
            try:
                images = convert_from_bytes(uploaded_file.read())
                if len(images) > 1:
                    pg = st.number_input("Page:", 1, len(images), 1)
                    image = images[pg - 1]
                else:
                    image = images[0]
            except Exception as e:
                st.error("Error loading PDF. Ensure 'poppler' is installed.")
        else:
            image = Image.open(uploaded_file)

        if image:
            image = image.convert("RGB")
            # Mobile-friendly canvas width
            canvas_width = min(800, st.sidebar.slider("Canvas Width", 200, 800, 600))
            w_percent = canvas_width / float(image.size[0])
            canvas_height = int(float(image.size[1]) * w_percent)
            bg_image = image.resize((canvas_width, canvas_height))

            # Canvas
            canvas_result = st_canvas(
                fill_color="rgba(255,255,255,0)",
                stroke_width=stroke_width,
                stroke_color=stroke_color,
                background_image=bg_image,
                height=canvas_height,
                width=canvas_width,
                drawing_mode=drawing_mode,
                key="canvas",
                display_toolbar=True
            )

            # Save PDF
            st.markdown("---")
            if st.button("💾 Save PDF"):
                if canvas_result and canvas_result.image_data is not None:
                    try:
                        edited = Image.fromarray(canvas_result.image_data.astype("uint8"), mode="RGBA")
                        final = bg_image.convert("RGBA")
                        edited = edited.resize(final.size)
                        final.alpha_composite(edited)
                        final = final.convert("RGB")
                        buf = io.BytesIO()
                        final.save(buf, format="PDF")
                        st.success("✅ Saved Successfully!")
                        st.download_button("📥 Download PDF", buf.getvalue(), "edited_doc.pdf")
                    except Exception as e:
                        st.error(f"Save failed: {e}")
                else:
                    st.warning("No changes made.")

# ==================================================
# 2️⃣ UNIVERSAL CONVERTER
# ==================================================
elif app_mode == "🔄 Universal Converter":
    st.header("🔄 Converters")
    tab1, tab2, tab3, tab4 = st.tabs(["PDF->Word", "Word->PDF", "Img->PDF", "Typewriter"])

    # PDF -> Word
    with tab1:
        f = st.file_uploader("PDF", type=['pdf'], key='p2w')
        if f and st.button("Convert to Word"):
            with open("t.pdf", "wb") as file:
                file.write(f.read())
            cv = Converter("t.pdf")
            cv.convert("c.docx")
            cv.close()
            with open("c.docx", "rb") as file:
                st.download_button("Download", file, "c.docx")

    # Word -> PDF
    with tab2:
        f = st.file_uploader("Word", type=['docx'], key='w2p')
        if f and st.button("Convert to PDF"):
            try:
                doc = Document(f)
                pdf = FPDF()
                pdf.set_auto_page_break(auto=True, margin=15)
                pdf.add_page()
                pdf.set_font("Arial", size=12)
                for p in doc.paragraphs:
                    safe_text = p.text.encode('latin-1', 'replace').decode('latin-1')
                    try:
                        pdf.multi_cell(0, 10, safe_text)
                    except:
                        pass
                st.download_button("Download", bytes(pdf.output()), "doc.pdf")
            except Exception as e:
                st.error(e)

    # Images -> PDF
    with tab3:
        imgs = st.file_uploader("Images", type=['jpg', 'png'], accept_multiple_files=True)
        if imgs and st.button("Convert"):
            pil = [Image.open(i).convert("RGB") for i in imgs]
            b = io.BytesIO()
            pil[0].save(b, format="PDF", save_all=True, append_images=pil[1:])
            st.download_button("Download", b.getvalue(), "images.pdf")

    # Hindi Typewriter
    with tab4:
        txt = st.text_area("Hindi Text:")
        sz = st.slider("Font Size", 10, 40, 16)
        if st.button("Convert"):
            if os.path.exists("Typewriter.ttf"):
                pdf = FPDF()
                pdf.add_page()
                pdf.add_font("Kruti", "", "Typewriter.ttf")
                pdf.set_font("Kruti", size=sz)
                try:
                    pdf.multi_cell(0, 10, convert_to_kruti(txt))
                    st.download_button("Download PDF", bytes(pdf.output()), "type.pdf")
                except Exception as e:
                    st.error(e)
            else:
                st.error("Typewriter.ttf missing")
