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

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------
st.set_page_config(page_title="PDF Editor & Converter", layout="wide")
st.title("📄 Professional PDF Tool")

# --------------------------------------------------
# HELPER: UNICODE TO KRUTI DEV
# --------------------------------------------------
def convert_to_kruti(text):
    text = text.replace("त्र", "=k").replace("ज्ञ", "%").replace("श्र", "J")
    chars = list(text)
    i = 0
    while i < len(chars):
        if chars[i] == 'ि' and i > 0:
            chars[i], chars[i-1] = chars[i-1], 'f'
        i += 1
    text = "".join(chars)

    mapping = {
        'ा':'k','ी':'h','ु':'q','ू':'w','ृ':'`','े':'s','ै':'S','ो':'ks','ौ':'kS',
        'ं':'a','ँ':'¡','ः':'%','्':'d','़':'+',
        'क':'d','ख':'[','ग':'x','घ':'?','च':'p','छ':'N','ज':'t','झ':'>',
        'ट':'V','ठ':'B','ड':'M','ढ':'<','ण':'.','त':'r','थ':'F','द':'n',
        'ध':'è','न':'u','प':'i','फ':'Q','ब':'c','भ':'H','म':'e',
        'य':';','र':'j','ल':'y','व':'b','श':'M','ष':'k','स':'l','ह':'v',
        '०':'0','१':'1','२':'2','३':'3','४':'4','५':'5','६':'6','७':'7','८':'8','९':'9'
    }

    return "".join(mapping.get(c, c) for c in text)

# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------
st.sidebar.title("🚀 Main Menu")
app_mode = st.sidebar.radio(
    "Go to:",
    ["✏️ PDF Direct Editor", "🔄 Universal Converter"]
)

# ==================================================
# 1️⃣ PDF DIRECT EDITOR
# ==================================================
if app_mode == "✏️ PDF Direct Editor":
    st.header("✏️ PDF Direct Editor")

    uploaded_file = st.file_uploader(
        "Upload PDF / Image",
        type=["pdf", "jpg", "png"]
    )

    col1, col2 = st.columns(2)
    with col1:
        drawing_mode = st.selectbox("Tool", ("rect", "text", "transform"))
    with col2:
        stroke_width = st.slider("Size", 1, 50, 10)

    stroke_color = "#000000"
    if drawing_mode == "text":
        stroke_color = st.color_picker("Text Color", "#000000")
    elif drawing_mode == "rect":
        stroke_color = "#FFFFFF"

    canvas_result = None

    if uploaded_file:
        image = None

        # --- PDF LOAD ---
        if uploaded_file.name.lower().endswith(".pdf"):
            try:
                images = convert_from_bytes(uploaded_file.read())
                page = st.number_input("Page", 1, len(images), 1)
                image = images[page - 1]
            except:
                st.error("PDF load failed. Poppler missing?")
        else:
            image = Image.open(uploaded_file)

        if image:
            image = image.convert("RGB")

            canvas_width = 800
            ratio = canvas_width / image.width
            canvas_height = int(image.height * ratio)
            bg_image = image.resize((canvas_width, canvas_height))

            canvas_result = st_canvas(
                background_image=bg_image,
                height=canvas_height,
                width=canvas_width,
                drawing_mode=drawing_mode,
                stroke_width=stroke_width,
                stroke_color=stroke_color,
                fill_color="rgba(255,255,255,1)",
                key="canvas",
            )

            st.markdown("---")

            if st.button("💾 Save as PDF"):
                if canvas_result and canvas_result.image_data is not None:
                    edited = Image.fromarray(
                        canvas_result.image_data.astype("uint8"),
                        mode="RGBA"
                    )
                    final = bg_image.convert("RGBA")
                    final.alpha_composite(edited)
                    final = final.convert("RGB")

                    buf = io.BytesIO()
                    final.save(buf, format="PDF")

                    st.download_button(
                        "⬇️ Download PDF",
                        buf.getvalue(),
                        "edited.pdf"
                    )
                else:
                    st.warning("No edits found.")

# ==================================================
# 2️⃣ UNIVERSAL CONVERTER
# ==================================================
else:
    st.header("🔄 Universal Converter")

    tab1, tab2, tab3, tab4 = st.tabs(
        ["PDF → Word", "Word → PDF", "Image → PDF", "Typewriter"]
    )

    # --- PDF → WORD ---
    with tab1:
        f = st.file_uploader("Upload PDF", type=["pdf"])
        if f and st.button("Convert"):
            with open("temp.pdf", "wb") as fp:
                fp.write(f.read())
            cv = Converter("temp.pdf")
            cv.convert("out.docx")
            cv.close()
            with open("out.docx", "rb") as fp:
                st.download_button("Download", fp, "converted.docx")

    # --- WORD → PDF ---
    with tab2:
        f = st.file_uploader("Upload Word", type=["docx"])
        if f and st.button("Convert"):
            doc = Document(f)
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            for p in doc.paragraphs:
                text = p.text.encode("latin-1", "replace").decode("latin-1")
                pdf.multi_cell(0, 8, text)
            st.download_button("Download", bytes(pdf.output()), "word.pdf")

    # --- IMAGE → PDF ---
    with tab3:
        imgs = st.file_uploader(
            "Upload Images",
            type=["jpg", "png"],
            accept_multiple_files=True
        )
        if imgs and st.button("Convert"):
            images = [Image.open(i).convert("RGB") for i in imgs]
            buf = io.BytesIO()
            images[0].save(buf, save_all=True, append_images=images[1:], format="PDF")
            st.download_button("Download", buf.getvalue(), "images.pdf")

    # --- TYPEWRITER ---
    with tab4:
        txt = st.text_area("Hindi Text")
        size = st.slider("Font Size", 10, 40, 16)

        if st.button("Generate PDF"):
            if not os.path.exists("Typewriter.ttf"):
                st.error("Typewriter.ttf missing")
            else:
                pdf = FPDF()
                pdf.add_page()
                pdf.add_font("Kruti", "", "Typewriter.ttf", uni=True)
                pdf.set_font("Kruti", size=size)
                pdf.multi_cell(0, 10, convert_to_kruti(txt))
                st.download_button(
                    "Download",
                    bytes(pdf.output()),
                    "typewriter.pdf"
                )
