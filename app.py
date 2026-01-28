import streamlit as st
from streamlit_drawable_canvas import st_canvas
from pdf2image import convert_from_bytes
from pdf2docx import Converter
from fpdf import FPDF
from PIL import Image
from docx import Document
import io, os, numpy as np

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------
st.set_page_config(page_title="PDF Editor & Converter", layout="wide")
st.title("📄 Professional PDF Editor & Converter")

# --------------------------------------------------
# HELPER: UNICODE → KRUTI DEV
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
        'य':';','र':'j','ल':'y','व':'b','श':'M','ष':'k','स':'l','ह':'v'
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
# ✏️ PDF DIRECT EDITOR
# ==================================================
if app_mode == "✏️ PDF Direct Editor":
    st.header("✏️ PDF Direct Editor (Editable)")

    uploaded_file = st.file_uploader(
        "Upload PDF / Image",
        type=["pdf", "jpg", "png"]
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        drawing_mode = st.selectbox(
            "Tool",
            ("text", "rect", "transform")
        )
    with col2:
        stroke_width = st.slider("Stroke Size", 1, 20, 2)
    with col3:
        stroke_color = st.color_picker("Color", "#000000")

    canvas_result = None

    if uploaded_file:
        image = None

        # --- LOAD PDF / IMAGE ---
        if uploaded_file.name.lower().endswith(".pdf"):
            images = convert_from_bytes(uploaded_file.read(), dpi=200)
            page = st.number_input("Page", 1, len(images), 1)
            image = images[page - 1]
        else:
            image = Image.open(uploaded_file)

        image = image.convert("RGB")

        # --- RESIZE ---
        canvas_width = 900
        ratio = canvas_width / image.width
        canvas_height = int(image.height * ratio)
        bg_image = image.resize((canvas_width, canvas_height))

        # --- CANVAS ---
        canvas_result = st_canvas(
            background_image=bg_image,
            height=canvas_height,
            width=canvas_width,
            drawing_mode=drawing_mode,
            stroke_width=stroke_width,
            stroke_color=stroke_color,
            fill_color="rgba(0,0,0,0)",  # ⭐ transparent
            text_color=stroke_color,
            key="canvas",
            update_streamlit=True,
            display_toolbar=True,   # ⭐ zoom, pan, select
        )

        st.info(
            "✏️ Text edit: text par double-click karein | "
            "🖱️ Zoom: mouse wheel | "
            "✋ Pan: space + drag | "
            "🔄 Transform: move / resize"
        )

        # --- SAVE ---
        st.markdown("---")
        if st.button("💾 Save Edited PDF"):
            if canvas_result and canvas_result.image_data is not None:
                edited = Image.fromarray(
                    canvas_result.image_data.astype("uint8"),
                    "RGBA"
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
# 🔄 UNIVERSAL CONVERTER
# ==================================================
else:
    st.header("🔄 Universal Converter")

    tab1, tab2, tab3, tab4 = st.tabs(
        ["PDF → Word", "Word → PDF", "Image → PDF", "Typewriter"]
    )

    # PDF → WORD
    with tab1:
        f = st.file_uploader("Upload PDF", type=["pdf"])
        if f and st.button("Convert"):
            with open("temp.pdf", "wb") as fp:
                fp.write(f.read())
            cv = Converter("temp.pdf")
            cv.convert("output.docx")
            cv.close()
            with open("output.docx", "rb") as fp:
                st.download_button("Download", fp, "converted.docx")

    # WORD → PDF
    with tab2:
        f = st.file_uploader("Upload Word", type=["docx"])
        if f and st.button("Convert"):
            doc = Document(f)
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            for p in doc.paragraphs:
                t = p.text.encode("latin-1", "replace").decode("latin-1")
                pdf.multi_cell(0, 8, t)
            st.download_button("Download", bytes(pdf.output()), "word.pdf")

    # IMAGE → PDF
    with tab3:
        imgs = st.file_uploader(
            "Upload Images",
            type=["jpg", "png"],
            accept_multiple_files=True
        )
        if imgs and st.button("Convert"):
            images = [Image.open(i).convert("RGB") for i in imgs]
            buf = io.BytesIO()
            images[0].save(
                buf,
                save_all=True,
                append_images=images[1:],
                format="PDF"
            )
            st.download_button("Download", buf.getvalue(), "images.pdf")

    # TYPEWRITER
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
