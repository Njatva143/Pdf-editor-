import streamlit as st
from streamlit_drawable_canvas import st_canvas
from pdf2image import convert_from_bytes
from PIL import Image
import pytesseract
import io, numpy as np
from fpdf import FPDF

# --------------------------------------------------
# CONFIG
# --------------------------------------------------
st.set_page_config("Advanced PDF Editor", layout="wide")
st.title("📄 Advanced PDF Editor (Multi-Page + OCR + Editable)")

# --------------------------------------------------
# STATE
# --------------------------------------------------
if "page" not in st.session_state:
    st.session_state.page = 0

# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------
st.sidebar.header("⚙️ Tools")
mode = st.sidebar.selectbox(
    "Mode",
    ["PDF Editor", "OCR Editor"]
)

# ==================================================
# 📄 PDF EDITOR (MULTI-PAGE)
# ==================================================
if mode == "PDF Editor":

    uploaded = st.file_uploader("Upload PDF", type=["pdf"])

    if uploaded:
        pages = convert_from_bytes(uploaded.read(), dpi=200)

        colA, colB, colC = st.columns([1,2,1])
        with colA:
            if st.button("⬅ Prev") and st.session_state.page > 0:
                st.session_state.page -= 1
        with colC:
            if st.button("Next ➡") and st.session_state.page < len(pages)-1:
                st.session_state.page += 1

        st.info(f"Page {st.session_state.page + 1} / {len(pages)}")

        img = pages[st.session_state.page].convert("RGB")

        w = 900
        ratio = w / img.width
        h = int(img.height * ratio)
        bg = img.resize((w, h))

        tool = st.selectbox("Tool", ["text", "rect", "transform"])
        color = st.color_picker("Color", "#000000")

        canvas = st_canvas(
            background_image=bg,
            width=w,
            height=h,
            drawing_mode=tool,
            stroke_color=color,
            fill_color="rgba(0,0,0,0)",
            update_streamlit=True,
            display_toolbar=True,
            key="canvas"
        )

        if st.button("💾 Save Page as PDF"):
            overlay = Image.fromarray(
                canvas.image_data.astype("uint8"),
                "RGBA"
            )
            final = bg.convert("RGBA")
            final.alpha_composite(overlay)
            final = final.convert("RGB")

            buf = io.BytesIO()
            final.save(buf, format="PDF")

            st.download_button(
                "Download PDF",
                buf.getvalue(),
                f"page_{st.session_state.page+1}.pdf"
            )

# ==================================================
# 🔍 OCR EDITOR
# ==================================================
else:
    st.header("🔍 OCR Text Editor")

    img_file = st.file_uploader(
        "Upload Image / Scanned PDF Page",
        type=["png", "jpg", "jpeg"]
    )

    if img_file:
        img = Image.open(img_file).convert("RGB")
        st.image(img, caption="Original")

        if st.button("Run OCR"):
            text = pytesseract.image_to_string(img, lang="hin+eng")
            st.session_state.ocr_text = text

    if "ocr_text" in st.session_state:
        edited = st.text_area(
            "✏️ Editable OCR Text",
            st.session_state.ocr_text,
            height=300
        )

        if st.button("Save as PDF"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)

            for line in edited.split("\n"):
                safe = line.encode("latin-1", "replace").decode("latin-1")
                pdf.multi_cell(0, 8, safe)

            st.download_button(
                "Download OCR PDF",
                bytes(pdf.output()),
                "ocr_output.pdf"
            )
