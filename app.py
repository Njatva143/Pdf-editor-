import streamlit as st
from streamlit_drawable_canvas import st_canvas
from pdf2image import convert_from_bytes
from PIL import Image
import pytesseract
from PyPDF2 import PdfReader, PdfWriter
import io
import uuid

# =====================================================
# CONFIG
# =====================================================
st.set_page_config("Advanced PDF Editor", layout="wide")
st.title("📄 Advanced Professional PDF Editor")

MAX_MB = 15
MAX_PAGES = 15
DPI = 300
CANVAS_WIDTH = 900

# =====================================================
# UTILITIES
# =====================================================
def check_file(file):
    if file.size > MAX_MB * 1024 * 1024:
        st.error("❌ File too large")
        st.stop()

def pdf_to_images(file):
    try:
        pages = convert_from_bytes(file.read(), dpi=DPI)
        if len(pages) > MAX_PAGES:
            st.error("❌ Too many pages")
            st.stop()
        return pages
    except Exception as e:
        st.error("PDF load failed (Poppler missing?)")
        st.error(e)
        st.stop()

def resize(img):
    ratio = CANVAS_WIDTH / img.width
    return img.resize((CANVAS_WIDTH, int(img.height * ratio)))

def save_pdf(images):
    buf = io.BytesIO()
    images[0].save(buf, format="PDF", save_all=True, append_images=images[1:])
    return buf.getvalue()

def apply_password(pdf_bytes, password):
    reader = PdfReader(io.BytesIO(pdf_bytes))
    writer = PdfWriter()
    for p in reader.pages:
        writer.add_page(p)
    writer.encrypt(password)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()

def add_ocr_layer(image):
    text = pytesseract.image_to_string(image)
    return text

# =====================================================
# SIDEBAR
# =====================================================
st.sidebar.title("🧭 Tools")
tool = st.sidebar.radio(
    "Mode",
    ["Editor", "OCR", "Security"]
)

uploaded = st.sidebar.file_uploader("Upload PDF", type=["pdf"])

if not uploaded:
    st.info("Upload a PDF to start")
    st.stop()

check_file(uploaded)
pages = pdf_to_images(uploaded)

# =====================================================
# PAGE SELECT + THUMBNAILS
# =====================================================
st.sidebar.markdown("### 📑 Pages")
cols = st.sidebar.columns(3)
selected_page = 0

for i, img in enumerate(pages):
    with cols[i % 3]:
        if st.button(f"{i+1}"):
            selected_page = i

page_img = pages[selected_page].convert("RGB")
canvas_bg = resize(page_img)

# =====================================================
# EDITOR MODE
# =====================================================
if tool == "Editor":

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        mode = st.selectbox("Tool", ["freedraw", "rect", "text"])
    with c2:
        size = st.slider("Size", 1, 40, 5)
    with c3:
        color = st.color_picker("Color", "#FF0000")
    with c4:
        rotate = st.selectbox("Rotate", [0, 90, 180, 270])

    if rotate:
        page_img = page_img.rotate(-rotate, expand=True)
        canvas_bg = resize(page_img)

    canvas = st_canvas(
        background_image=canvas_bg,
        drawing_mode=mode,
        stroke_width=size,
        stroke_color=color,
        fill_color="rgba(0,0,0,0)",
        height=canvas_bg.height,
        width=canvas_bg.width,
        key=str(uuid.uuid4())
    )

    if st.button("💾 Save Changes"):
        if canvas.image_data is not None:
            edited = Image.fromarray(canvas.image_data.astype("uint8"))
            edited = edited.resize(page_img.size)

            final = page_img.convert("RGBA")
            final.alpha_composite(edited.convert("RGBA"))

            pages[selected_page] = final.convert("RGB")
            st.success("Saved")

# =====================================================
# OCR MODE
# =====================================================
elif tool == "OCR":

    st.warning("OCR makes PDF searchable, not editable")

    if st.button("Run OCR on this page"):
        text = add_ocr_layer(page_img)
        st.text_area("Extracted Text", text, height=300)

# =====================================================
# SECURITY MODE
# =====================================================
elif tool == "Security":

    password = st.text_input("Set PDF Password", type="password")

    if st.button("🔐 Save Secured PDF"):
        pdf = save_pdf(pages)
        if password:
            pdf = apply_password(pdf, password)

        st.download_button(
            "📥 Download Protected PDF",
            pdf,
            "secured.pdf",
            "application/pdf"
        )

# =====================================================
# FINAL EXPORT
# =====================================================
st.markdown("---")
if st.button("📤 Export Final PDF"):
    pdf = save_pdf(pages)
    st.download_button(
        "Download PDF",
        pdf,
        "final_document.pdf",
        "application/pdf"
    )
    
