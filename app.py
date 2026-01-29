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
tool = st.sidebar.radio(
    "Mode",
    ["Editor", "OCR", "PDF → Word (Editable)", "Security"]
)

uploaded = st.sidebar.file_uploader("Upload PDF", type=["pdf"])

if not uploaded:
    st.info("Upload a PDF to start")
    st.stop()
tool = st.sidebar.radio(
    "Mode",
    [
        "Editor",
        "OCR",
        "PDF → Word (Editable)",
        "Word → PDF",
        "Security"
    ]
)

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
        mode = st.selectbox("Tool", ["freedraw", "edit", "rect", "text"])
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
    key=f"canvas_{selected_page}"
        
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

    if st.button("📄 OCR → Word (Editable)"):

    from docx import Document
    import tempfile
    import os

    with st.spinner("Running OCR and creating Word file..."):
        doc = Document()

        for i, img in enumerate(pages):
            text = pytesseract.image_to_string(img)
            doc.add_heading(f"Page {i+1}", level=2)
            doc.add_paragraph(text)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp_docx:
            doc.save(tmp_docx.name)

            with open(tmp_docx.name, "rb") as f:
                st.success("✅ OCR Word file ready")
                st.download_button(
                    "📥 Download OCR Editable Word",
                    f.read(),
                    "ocr_editable.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )

        os.remove(tmp_docx.name)
        
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
# PDF → WORD (EDITABLE)
# =====================================================
elif tool == "PDF → Word (Editable)":

    st.info(
        "ℹ️ Ye feature real text editing ke liye hai.\n"
        "PDF ko Word (DOCX) me convert karke edit kar sakte hain."
    )

    from pdf2docx import Converter
    import tempfile
    import os

    if st.button("📝 Convert PDF to Word"):
        with st.spinner("Converting PDF to editable Word..."):

            # Temporary files (cloud-safe)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
                tmp_pdf.write(uploaded.getbuffer())
                pdf_path = tmp_pdf.name

            docx_path = pdf_path.replace(".pdf", ".docx")

            try:
                cv = Converter(pdf_path)
                cv.convert(docx_path)
                cv.close()

                with open(docx_path, "rb") as f:
                    st.success("✅ Conversion successful")
                    st.download_button(
                        "📥 Download Editable Word File",
                        f.read(),
                        "editable.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )

            except Exception as e:
                st.error("❌ Conversion failed")
                st.error(str(e))

            finally:
                # Cleanup
                if os.path.exists(pdf_path):
                    os.remove(pdf_path)
                if os.path.exists(docx_path):
                    os.remove(docx_path)
# =====================================================
# WORD → PDF
# =====================================================
elif tool == "Word → PDF":

    st.info(
        "ℹ️ Edited Word file upload karein aur usse PDF me convert karein."
    )

    from docx2pdf import convert
    import tempfile
    import os

    word_file = st.file_uploader(
        "Upload Word File (.docx)",
        type=["docx"]
    )

    if word_file and st.button("🔁 Convert Word to PDF"):
        with st.spinner("Converting Word to PDF..."):

            with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp_docx:
                tmp_docx.write(word_file.getbuffer())
                docx_path = tmp_docx.name

            pdf_path = docx_path.replace(".docx", ".pdf")

            try:
                convert(docx_path, pdf_path)

                with open(pdf_path, "rb") as f:
                    st.success("✅ PDF ready")
                    st.download_button(
                        "📥 Download PDF",
                        f.read(),
                        "converted.pdf",
                        mime="application/pdf"
                    )

            except Exception as e:
                st.error("❌ Conversion failed")
                st.error(str(e))

            finally:
                if os.path.exists(docx_path):
                    os.remove(docx_path)
                if os.path.exists(pdf_path):
                    os.remove(pdf_path)
                    
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
    
