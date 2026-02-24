import base64
import copy
import io
import logging
import os
import shutil
import subprocess
import tempfile
import time
import uuid
import zipfile
from pathlib import Path

import fitz
from deep_translator import GoogleTranslator
from docx import Document
from flask import Flask, after_this_request, g, redirect, render_template, request, send_file, url_for
from pdf2docx import Converter
from PIL import Image
from pypdf import PdfReader, PdfWriter
from werkzeug.utils import secure_filename

try:
    import pytesseract
except Exception:
    pytesseract = None

try:
    import speech_recognition as sr
except Exception:
    sr = None

try:
    import yt_dlp
except Exception:
    yt_dlp = None

try:
    from pydub import AudioSegment
except Exception:
    AudioSegment = None

try:
    from docx2pdf import convert as docx2pdf_convert
except Exception:
    docx2pdf_convert = None

logging.getLogger("pdf2docx").setLevel(logging.WARNING)

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
TEMP_DIR = BASE_DIR / "temp"
RUNTIME_DIR = Path(tempfile.gettempdir()) / "pdftoword_runtime"

for folder in (UPLOAD_DIR, OUTPUT_DIR, TEMP_DIR, RUNTIME_DIR):
    folder.mkdir(exist_ok=True)

TESSERACT_AVAILABLE = shutil.which("tesseract") is not None and pytesseract is not None

app = Flask(__name__)
MAX_UPLOAD_MB = int((os.environ.get("MAX_UPLOAD_MB") or "40").strip() or "40")
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 3600

TOOLS = [
    ("pdf-to-word", "PDF to Word"),
    ("word-to-pdf", "Word to PDF"),
    ("pdf-to-images", "PDF to Images"),
    ("images-to-pdf", "Images to PDF"),
    ("merge-pdf", "Merge PDFs"),
    ("split-pdf", "Split PDF"),
    ("compress-pdf", "Compress PDF"),
    ("protect-pdf", "Protect PDF"),
    ("unlock-pdf", "Unlock PDF"),
    ("sign-pdf", "Sign PDF"),
    ("remove-watermark", "Remove Watermark"),
    ("remove-password", "Remove Document Password"),
    ("ocr", "OCR / Text Extraction"),
    ("translate", "Translate Document"),
    ("transcribe-audio", "Transcribe Audio to TXT"),
    ("youtube-to-mp3", "YouTube to MP3"),
    ("youtube-to-mp4", "YouTube to MP4"),
    ("youtube-playlist-to-mp3", "YouTube Playlist to MP3"),
    ("youtube-playlist-to-mp4", "YouTube Playlist to MP4"),
    ("spotify-to-mp3", "Spotify to MP3"),
    ("spotify-playlist-to-mp3", "Spotify Playlist to MP3"),
]
TOOL_MAP = {slug: title for slug, title in TOOLS}
TOOL_DESC = {
    "pdf-to-word": "Convert PDF into editable DOCX, with optional translation.",
    "word-to-pdf": "Convert DOCX to PDF.",
    "pdf-to-images": "Export each PDF page as image.",
    "images-to-pdf": "Merge images into a single PDF.",
    "merge-pdf": "Combine multiple PDFs into one file.",
    "split-pdf": "Split PDF by pages or range.",
    "compress-pdf": "Reduce PDF file size.",
    "protect-pdf": "Apply a password to a PDF.",
    "unlock-pdf": "Remove PDF protection with a valid password.",
    "sign-pdf": "Add text and/or image signature into PDF.",
    "remove-watermark": "Try to remove text watermarks from PDF.",
    "remove-password": "Remove PDF password when current password is provided.",
    "ocr": "Extract text from PDFs and images.",
    "translate": "Translate DOCX, PDF or TXT documents.",
    "transcribe-audio": "Transcribe audio/video into TXT.",
    "youtube-to-mp3": "Extract audio from YouTube link as MP3.",
    "youtube-to-mp4": "Download YouTube video as MP4.",
    "spotify-to-mp3": "Convert Spotify links to MP3 (spotdl).",
    "youtube-playlist-to-mp3": "Convert YouTube playlist to MP3 ZIP.",
    "youtube-playlist-to-mp4": "Convert YouTube playlist to MP4 ZIP.",
    "spotify-playlist-to-mp3": "Convert Spotify playlist to MP3 ZIP.",
}
CATEGORY_ITEMS = {
    "conversao": ["pdf-to-word", "word-to-pdf", "pdf-to-images", "images-to-pdf"],
    "edicao": ["merge-pdf", "split-pdf", "compress-pdf", "sign-pdf", "remove-watermark"],
    "seguranca": ["protect-pdf", "unlock-pdf", "remove-password"],
    "texto": ["ocr", "translate", "transcribe-audio"],
    "media": [
        "youtube-to-mp3",
        "youtube-to-mp4",
        "youtube-playlist-to-mp3",
        "youtube-playlist-to-mp4",
        "spotify-to-mp3",
        "spotify-playlist-to-mp3",
    ],
}
FFMPEG_PATH = shutil.which("ffmpeg")
LIBREOFFICE_PATH = shutil.which("libreoffice") or shutil.which("soffice")
YTDLP_COOKIEFILE: Path | None = None
YTDLP_USER_AGENT = (
    os.environ.get("YTDLP_USER_AGENT")
    or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
).strip()
YTDLP_VISITOR_DATA = (os.environ.get("YTDLP_VISITOR_DATA") or "").strip()
YTDLP_PO_TOKEN = (os.environ.get("YTDLP_PO_TOKEN") or "").strip()
YTDLP_PLAYER_CLIENTS = [item.strip() for item in (os.environ.get("YTDLP_PLAYER_CLIENTS") or "android,web").split(",") if item.strip()]
ADSENSE_CLIENT = (os.environ.get("ADSENSE_CLIENT") or "").strip()
ADSENSE_SLOT_TOP = (os.environ.get("ADSENSE_SLOT_TOP") or "").strip()
ADSENSE_SLOT_INLINE = (os.environ.get("ADSENSE_SLOT_INLINE") or "").strip()
APP_VERSION = (os.environ.get("APP_VERSION") or os.environ.get("RENDER_GIT_COMMIT") or "dev").strip()


@app.before_request
def before_request_timer():
    g.request_start = time.perf_counter()


@app.after_request
def apply_global_response_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")

    if request.path.startswith("/static/"):
        response.headers.setdefault("Cache-Control", "public, max-age=86400")

    start = getattr(g, "request_start", None)
    if start is not None:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        response.headers["X-Response-Time-Ms"] = str(max(elapsed_ms, 0))
    return response


@app.context_processor
def inject_app_config():
    return {
        "max_upload_mb": MAX_UPLOAD_MB,
        "adsense_client": ADSENSE_CLIENT,
        "adsense_slot_top": ADSENSE_SLOT_TOP,
        "adsense_slot_inline": ADSENSE_SLOT_INLINE,
        "app_version": APP_VERSION,
    }


def unique_name(stem: str, suffix: str) -> str:
    safe_stem = secure_filename(stem) or "file"
    return f"{safe_stem}_{uuid.uuid4().hex[:10]}{suffix}"


def safe_download_name(raw_name: str, ext: str, fallback: str) -> str:
    name = (raw_name or "").strip()
    if not name:
        name = fallback
    invalid = '<>:"/\\|?*'
    for char in invalid:
        name = name.replace(char, " ")
    name = " ".join(name.split()).strip(". ")
    if not name:
        name = fallback
    return f"{name}{ext}"


def zip_files(files: list[Path], zip_path: Path) -> None:
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for item in files:
            zf.write(item, item.name)


def get_ytdlp_cookiefile() -> str | None:
    global YTDLP_COOKIEFILE
    if YTDLP_COOKIEFILE and YTDLP_COOKIEFILE.exists():
        return str(YTDLP_COOKIEFILE)

    cookie_path = (os.environ.get("YTDLP_COOKIES_FILE") or "").strip()
    if cookie_path and Path(cookie_path).exists():
        YTDLP_COOKIEFILE = Path(cookie_path)
        return str(YTDLP_COOKIEFILE)

    cookie_b64 = (os.environ.get("YTDLP_COOKIES_B64") or "").strip()
    if not cookie_b64:
        return None

    try:
        raw = base64.b64decode(cookie_b64.encode("utf-8"), validate=True)
        text = raw.decode("utf-8", errors="ignore")
        if "# Netscape HTTP Cookie File" not in text:
            return None
        cookie_file = RUNTIME_DIR / "youtube_cookies.txt"
        cookie_file.write_text(text, encoding="utf-8")
        YTDLP_COOKIEFILE = cookie_file
        return str(YTDLP_COOKIEFILE)
    except Exception:
        return None


def get_ytdlp_header_hints() -> tuple[str, str]:
    visitor_data = YTDLP_VISITOR_DATA
    po_token = YTDLP_PO_TOKEN
    if visitor_data and po_token:
        return visitor_data, po_token

    candidates = [BASE_DIR / "yt_headers.txt", BASE_DIR.parent / "yt_headers.txt"]
    for file_path in candidates:
        if not file_path.exists():
            continue
        try:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
            for raw_line in text.splitlines():
                line = raw_line.strip()
                if ":" not in line:
                    continue
                key, value = line.split(":", 1)
                key = key.strip().lower()
                value = value.strip()
                if not visitor_data and key in {"x-goog-visitor-id", "x-visitor-data"} and value:
                    visitor_data = value
                if not po_token and key in {"x-youtube-identity-token", "x-po-token"} and value:
                    po_token = value
        except Exception:
            continue
        if visitor_data and po_token:
            break
    return visitor_data, po_token


def ytdlp_user_message(prefix: str, exc: Exception) -> str:
    detail = str(exc)
    if "Sign in to confirm you\u2019re not a bot" in detail or "Sign in to confirm you're not a bot" in detail:
        return (
            f"{prefix}: YouTube pediu autenticacao. "
            "No Render, define YTDLP_COOKIES_B64 (cookies Netscape) e opcionalmente "
            "YTDLP_PO_TOKEN + YTDLP_VISITOR_DATA para links mais bloqueados."
        )
    return f"{prefix}: {detail}"


def build_ytdlp_opts(out_template: str, download_format: str, playlist: bool, extract_mp3: bool) -> dict:
    visitor_data, po_token = get_ytdlp_header_hints()
    opts = {
        "format": download_format,
        "outtmpl": out_template,
        "proxy": "",
        "nopart": True,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": not playlist,
        "http_headers": {"User-Agent": YTDLP_USER_AGENT, "Accept-Language": "en-US,en;q=0.9"},
        "retries": 3,
        "fragment_retries": 3,
        "extractor_retries": 3,
        "socket_timeout": 30,
    }
    if FFMPEG_PATH:
        opts["ffmpeg_location"] = FFMPEG_PATH
    if extract_mp3:
        opts["postprocessors"] = [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}]

    youtube_args: dict[str, list[str]] = {}
    if YTDLP_PLAYER_CLIENTS:
        youtube_args["player_client"] = YTDLP_PLAYER_CLIENTS
    if visitor_data:
        youtube_args["visitor_data"] = [visitor_data]
    if po_token:
        youtube_args["po_token"] = [f"web+{po_token}"]
    if youtube_args:
        opts["extractor_args"] = {"youtube": youtube_args}

    cookiefile = get_ytdlp_cookiefile()
    if cookiefile:
        opts["cookiefile"] = cookiefile
    return opts


def ytdlp_extract_with_fallback(url: str, opts: dict) -> tuple[dict, Path]:
    attempts = [
        tuple(YTDLP_PLAYER_CLIENTS),
        ("android",),
        ("tv", "ios", "android"),
        ("mweb", "android", "web"),
    ]
    seen = set()
    ordered_attempts: list[tuple[str, ...]] = []
    for attempt in attempts:
        clean = tuple(item for item in attempt if item)
        if clean and clean not in seen:
            ordered_attempts.append(clean)
            seen.add(clean)

    last_exc: Exception | None = None
    for player_clients in ordered_attempts:
        try:
            local_opts = copy.deepcopy(opts)
            extractor_args = local_opts.get("extractor_args", {})
            youtube_args = extractor_args.get("youtube", {})
            youtube_args["player_client"] = list(player_clients)
            extractor_args["youtube"] = youtube_args
            local_opts["extractor_args"] = extractor_args
            with yt_dlp.YoutubeDL(local_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                prepared = Path(ydl.prepare_filename(info))
                return info, prepared
        except Exception as exc:
            last_exc = exc
            continue

    if last_exc is not None:
        raise last_exc
    raise RuntimeError("Falha desconhecida em yt-dlp.")


def queue_cleanup(paths: list[Path], dirs: list[Path] | None = None):
    dirs = dirs or []

    @after_this_request
    def cleanup(response):
        for path in paths:
            try:
                path.unlink(missing_ok=True)
            except Exception:
                pass
        for directory in dirs:
            try:
                shutil.rmtree(directory, ignore_errors=True)
            except Exception:
                pass
        return response


def translate_docx(docx_path: Path, source_lang: str, target_lang: str) -> None:
    for key in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "all_proxy"):
        os.environ.pop(key, None)
    os.environ["NO_PROXY"] = "*"
    os.environ["no_proxy"] = "*"

    doc = Document(str(docx_path))
    translator = GoogleTranslator(source=source_lang, target=target_lang)

    paragraphs = list(doc.paragraphs)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                paragraphs.extend(cell.paragraphs)

    for paragraph in paragraphs:
        if not paragraph.text.strip():
            continue
        for run in paragraph.runs:
            text = run.text
            if not text or not text.strip():
                continue
            lead_spaces = len(text) - len(text.lstrip())
            trail_spaces = len(text) - len(text.rstrip())
            lead = text[:lead_spaces] if lead_spaces else ""
            trail = text[len(text) - trail_spaces :] if trail_spaces else ""
            core = text.strip()
            if not core:
                continue
            try:
                translated = translator.translate(core)
                if translated:
                    run.text = lead + translated + trail
            except Exception:
                continue

    doc.save(str(docx_path))


def template_error(message: str, code: int = 400):
    tool_slug = (request.form.get("_tool") or request.args.get("tool") or "").strip()
    if tool_slug in TOOL_MAP:
        return (
            render_template(
                "tool_detail.html",
                tool_slug=tool_slug,
                tool_title=TOOL_MAP[tool_slug],
                tool_desc=TOOL_DESC.get(tool_slug, ""),
                tools=TOOLS,
                category_items=CATEGORY_ITEMS,
                tool_map=TOOL_MAP,
                error=message,
                tesseract_available=TESSERACT_AVAILABLE,
            ),
            code,
        )
    return render_template("tools_list.html", tools=TOOLS, tool_desc=TOOL_DESC, category_items=CATEGORY_ITEMS, tool_map=TOOL_MAP, error=message), code


@app.get("/")
def home():
    return render_template("home.html", tools=TOOLS, tool_desc=TOOL_DESC, category_items=CATEGORY_ITEMS, tool_map=TOOL_MAP)


@app.get("/index")
def index_legacy():
    return render_template("index.html")


@app.get("/converter")
def converter_redirect():
    return redirect(url_for("tools_page"))


@app.get("/converter-legacy")
def converter_legacy():
    return render_template("converter.html")


@app.get("/ferramentas")
def tools_page():
    return render_template("tools_list.html", tools=TOOLS, tool_desc=TOOL_DESC, category_items=CATEGORY_ITEMS, tool_map=TOOL_MAP)


@app.get("/ferramentas/<tool_slug>")
def tool_detail(tool_slug: str):
    if tool_slug not in TOOL_MAP:
        return template_error("Ferramenta nÃ£o encontrada.", 404)
    return render_template(
        "tool_detail.html",
        tool_slug=tool_slug,
        tool_title=TOOL_MAP[tool_slug],
        tool_desc=TOOL_DESC.get(tool_slug, ""),
        tools=TOOLS,
        category_items=CATEGORY_ITEMS,
        tool_map=TOOL_MAP,
        tesseract_available=TESSERACT_AVAILABLE,
    )


@app.post("/tools/pdf-to-word")
def pdf_to_word():
    uploaded = request.files.get("pdf_file")
    if not uploaded or not uploaded.filename.lower().endswith(".pdf"):
        return template_error("Envie um ficheiro PDF vÃ¡lido.")

    stem = Path(uploaded.filename).stem
    input_path = UPLOAD_DIR / unique_name(stem, ".pdf")
    output_path = OUTPUT_DIR / unique_name(stem, ".docx")

    translate = request.form.get("translate") == "on"
    source_lang = (request.form.get("source_lang") or "auto").strip() or "auto"
    target_lang = (request.form.get("target_lang") or "pt").strip() or "pt"

    uploaded.save(input_path)

    try:
        cv = Converter(str(input_path))
        cv.convert(str(output_path))
        cv.close()

        if translate:
            translate_docx(output_path, source_lang, target_lang)

        queue_cleanup([input_path, output_path])
        suffix = f"_{target_lang.upper()}" if translate else ""
        return send_file(str(output_path), as_attachment=True, download_name=f"{secure_filename(stem)}{suffix}.docx")
    except Exception as exc:
        return template_error(f"Falha na conversÃ£o PDF para Word: {exc}", 500)


@app.post("/convert")
def pdf_to_word_legacy_alias():
    # Legacy form action used by old landing pages.
    return pdf_to_word()


@app.post("/tools/word-to-pdf")
def word_to_pdf():
    uploaded = request.files.get("word_file")
    if not uploaded or not uploaded.filename.lower().endswith(".docx"):
        return template_error("Envie um ficheiro DOCX vÃ¡lido.")

    stem = Path(uploaded.filename).stem
    input_path = UPLOAD_DIR / unique_name(stem, ".docx")
    output_path = OUTPUT_DIR / unique_name(stem, ".pdf")
    uploaded.save(input_path)

    try:
        converted = False

        # Windows/macOS path via docx2pdf
        if docx2pdf_convert is not None:
            try:
                docx2pdf_convert(str(input_path), str(output_path))
                converted = output_path.exists()
            except Exception:
                converted = False

        # Linux/server fallback via LibreOffice headless
        if not converted and LIBREOFFICE_PATH:
            cmd = [
                LIBREOFFICE_PATH,
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                str(output_path.parent),
                str(input_path),
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            if proc.returncode == 0:
                lo_pdf = output_path.parent / f"{input_path.stem}.pdf"
                if lo_pdf.exists():
                    if lo_pdf != output_path:
                        if output_path.exists():
                            output_path.unlink(missing_ok=True)
                        lo_pdf.replace(output_path)
                    converted = True

        if not converted or not output_path.exists():
            raise RuntimeError(
                "DOCX->PDF conversion unavailable. On Linux, install LibreOffice."
            )
        queue_cleanup([input_path, output_path])
        return send_file(str(output_path), as_attachment=True, download_name=f"{secure_filename(stem)}.pdf")
    except Exception as exc:
        msg = "Word to PDF failed. Install LibreOffice on Linux or Microsoft Word/docx2pdf on Windows."
        return template_error(f"{msg} Erro: {exc}", 500)


@app.post("/tools/pdf-to-images")
def pdf_to_images():
    uploaded = request.files.get("pdf_file_images")
    if not uploaded or not uploaded.filename.lower().endswith(".pdf"):
        return template_error("Envie um PDF vÃ¡lido para converter em imagens.")

    stem = Path(uploaded.filename).stem
    input_path = UPLOAD_DIR / unique_name(stem, ".pdf")
    uploaded.save(input_path)

    scale = float(request.form.get("scale") or 2.0)
    scale = max(1.0, min(4.0, scale))

    work_dir = TEMP_DIR / unique_name(stem, "")
    work_dir.mkdir(parents=True, exist_ok=True)
    zip_path = OUTPUT_DIR / unique_name(stem, ".zip")

    try:
        doc = fitz.open(str(input_path))
        for idx, page in enumerate(doc, start=1):
            pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            img_path = work_dir / f"{secure_filename(stem)}_p{idx}.png"
            pix.save(str(img_path))
        doc.close()

        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for img_file in sorted(work_dir.glob("*.png")):
                zf.write(img_file, img_file.name)

        queue_cleanup([input_path, zip_path], [work_dir])
        return send_file(str(zip_path), as_attachment=True, download_name=f"{secure_filename(stem)}_images.zip")
    except Exception as exc:
        return template_error(f"Falha em PDF para imagens: {exc}", 500)


@app.post("/tools/images-to-pdf")
def images_to_pdf():
    files = request.files.getlist("image_files")
    images = [f for f in files if f and f.filename]
    if not images:
        return template_error("Envie uma ou mais imagens (PNG/JPG).")

    saved_paths: list[Path] = []
    output_path = OUTPUT_DIR / unique_name("images_to_pdf", ".pdf")

    try:
        pil_images = []
        for item in images:
            ext = Path(item.filename).suffix.lower()
            if ext not in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"}:
                continue
            img_path = UPLOAD_DIR / unique_name(Path(item.filename).stem, ext)
            item.save(img_path)
            saved_paths.append(img_path)
            pil_images.append(Image.open(img_path).convert("RGB"))

        if not pil_images:
            return template_error("Nenhuma imagem vÃ¡lida foi enviada.")

        first = pil_images[0]
        rest = pil_images[1:]
        first.save(str(output_path), save_all=True, append_images=rest)

        for img in pil_images:
            img.close()

        queue_cleanup(saved_paths + [output_path])
        return send_file(str(output_path), as_attachment=True, download_name="images_convertido.pdf")
    except Exception as exc:
        return template_error(f"Falha em imagens para PDF: {exc}", 500)


@app.post("/tools/merge-pdf")
def merge_pdf():
    files = request.files.getlist("merge_files")
    pdfs = [f for f in files if f and f.filename and f.filename.lower().endswith(".pdf")]
    if len(pdfs) < 2:
        return template_error("Envie pelo menos 2 PDFs para juntar.")

    saved_paths: list[Path] = []
    output_path = OUTPUT_DIR / unique_name("pdf_unido", ".pdf")

    try:
        writer = PdfWriter()
        for item in pdfs:
            in_path = UPLOAD_DIR / unique_name(Path(item.filename).stem, ".pdf")
            item.save(in_path)
            saved_paths.append(in_path)

            reader = PdfReader(str(in_path))
            if reader.is_encrypted:
                return template_error(f"PDF '{item.filename}' estÃ¡ protegido. Desbloqueie primeiro.")
            for page in reader.pages:
                writer.add_page(page)

        with output_path.open("wb") as f:
            writer.write(f)

        queue_cleanup(saved_paths + [output_path])
        return send_file(str(output_path), as_attachment=True, download_name="pdf_unido.pdf")
    except Exception as exc:
        return template_error(f"Falha ao juntar PDFs: {exc}", 500)


@app.post("/tools/split-pdf")
def split_pdf():
    uploaded = request.files.get("split_file")
    if not uploaded or not uploaded.filename.lower().endswith(".pdf"):
        return template_error("Envie um PDF vÃ¡lido para dividir.")

    mode = request.form.get("split_mode", "all")
    stem = Path(uploaded.filename).stem
    input_path = UPLOAD_DIR / unique_name(stem, ".pdf")
    uploaded.save(input_path)

    try:
        reader = PdfReader(str(input_path))
        if reader.is_encrypted:
            return template_error("PDF estÃ¡ protegido. Desbloqueie primeiro.")

        total = len(reader.pages)

        if mode == "range":
            start = int(request.form.get("start_page") or 1)
            end = int(request.form.get("end_page") or total)
            start = max(1, min(start, total))
            end = max(start, min(end, total))

            writer = PdfWriter()
            for idx in range(start - 1, end):
                writer.add_page(reader.pages[idx])

            output_path = OUTPUT_DIR / unique_name(f"{stem}_{start}_{end}", ".pdf")
            with output_path.open("wb") as f:
                writer.write(f)

            queue_cleanup([input_path, output_path])
            return send_file(str(output_path), as_attachment=True, download_name=f"{secure_filename(stem)}_{start}_{end}.pdf")

        work_dir = TEMP_DIR / unique_name(stem, "")
        work_dir.mkdir(parents=True, exist_ok=True)
        zip_path = OUTPUT_DIR / unique_name(f"{stem}_split", ".zip")

        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for i in range(total):
                writer = PdfWriter()
                writer.add_page(reader.pages[i])
                part_name = f"{secure_filename(stem)}_p{i + 1}.pdf"
                part_path = work_dir / part_name
                with part_path.open("wb") as f:
                    writer.write(f)
                zf.write(part_path, part_name)

        queue_cleanup([input_path, zip_path], [work_dir])
        return send_file(str(zip_path), as_attachment=True, download_name=f"{secure_filename(stem)}_split.zip")
    except Exception as exc:
        return template_error(f"Falha ao dividir PDF: {exc}", 500)


@app.post("/tools/compress-pdf")
def compress_pdf():
    uploaded = request.files.get("compress_file")
    if not uploaded or not uploaded.filename.lower().endswith(".pdf"):
        return template_error("Envie um PDF vÃ¡lido para compressÃ£o.")

    stem = Path(uploaded.filename).stem
    input_path = UPLOAD_DIR / unique_name(stem, ".pdf")
    output_path = OUTPUT_DIR / unique_name(f"{stem}_compressed", ".pdf")
    uploaded.save(input_path)

    try:
        doc = fitz.open(str(input_path))
        doc.save(str(output_path), garbage=4, deflate=True, clean=True)
        doc.close()

        queue_cleanup([input_path, output_path])
        return send_file(str(output_path), as_attachment=True, download_name=f"{secure_filename(stem)}_compressed.pdf")
    except Exception as exc:
        return template_error(f"Falha ao comprimir PDF: {exc}", 500)


@app.post("/tools/protect-pdf")
def protect_pdf():
    uploaded = request.files.get("protect_file")
    password = (request.form.get("password") or "").strip()
    owner_password = (request.form.get("owner_password") or "").strip() or password

    if not uploaded or not uploaded.filename.lower().endswith(".pdf"):
        return template_error("Envie um PDF vÃ¡lido para proteger.")
    if not password:
        return template_error("Defina a palavra-passe do PDF.")

    stem = Path(uploaded.filename).stem
    input_path = UPLOAD_DIR / unique_name(stem, ".pdf")
    output_path = OUTPUT_DIR / unique_name(f"{stem}_protected", ".pdf")
    uploaded.save(input_path)

    try:
        reader = PdfReader(str(input_path))
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        writer.encrypt(user_password=password, owner_password=owner_password)

        with output_path.open("wb") as f:
            writer.write(f)

        queue_cleanup([input_path, output_path])
        return send_file(str(output_path), as_attachment=True, download_name=f"{secure_filename(stem)}_protected.pdf")
    except Exception as exc:
        return template_error(f"Falha ao proteger PDF: {exc}", 500)


@app.post("/tools/unlock-pdf")
def unlock_pdf():
    uploaded = request.files.get("unlock_file")
    password = (request.form.get("unlock_password") or "").strip()

    if not uploaded or not uploaded.filename.lower().endswith(".pdf"):
        return template_error("Envie um PDF vÃ¡lido para desbloquear.")
    if not password:
        return template_error("Indique a palavra-passe para desbloquear.")

    stem = Path(uploaded.filename).stem
    input_path = UPLOAD_DIR / unique_name(stem, ".pdf")
    output_path = OUTPUT_DIR / unique_name(f"{stem}_unlocked", ".pdf")
    uploaded.save(input_path)

    try:
        reader = PdfReader(str(input_path))
        if reader.is_encrypted:
            decrypt_result = reader.decrypt(password)
            if decrypt_result == 0:
                return template_error("Palavra-passe invÃ¡lida para este PDF.", 403)

        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)

        with output_path.open("wb") as f:
            writer.write(f)

        queue_cleanup([input_path, output_path])
        return send_file(str(output_path), as_attachment=True, download_name=f"{secure_filename(stem)}_unlocked.pdf")
    except Exception as exc:
        return template_error(f"Falha ao desbloquear PDF: {exc}", 500)


@app.post("/tools/sign-pdf")
def sign_pdf():
    uploaded = request.files.get("sign_file")
    signature_image = request.files.get("signature_image")
    signature_text = (request.form.get("signature_text") or "Assinado digitalmente").strip()

    if not uploaded or not uploaded.filename.lower().endswith(".pdf"):
        return template_error("Envie um PDF vÃ¡lido para assinar.")

    page_choice = (request.form.get("signature_page") or "last").strip()

    stem = Path(uploaded.filename).stem
    input_path = UPLOAD_DIR / unique_name(stem, ".pdf")
    output_path = OUTPUT_DIR / unique_name(f"{stem}_signed", ".pdf")
    uploaded.save(input_path)

    sign_img_path = None
    if signature_image and signature_image.filename:
        img_ext = Path(signature_image.filename).suffix.lower() or ".png"
        sign_img_path = UPLOAD_DIR / unique_name("signature", img_ext)
        signature_image.save(sign_img_path)

    try:
        doc = fitz.open(str(input_path))
        page_idx = len(doc) - 1 if page_choice == "last" else 0
        page = doc[page_idx]

        rect = page.rect
        sign_rect = fitz.Rect(rect.width - 210, rect.height - 100, rect.width - 20, rect.height - 20)
        page.draw_rect(sign_rect, color=(0.2, 0.2, 0.2), fill=(1, 1, 1), width=0.8)

        if sign_img_path and sign_img_path.exists():
            img_rect = fitz.Rect(sign_rect.x0 + 6, sign_rect.y0 + 6, sign_rect.x0 + 80, sign_rect.y1 - 6)
            page.insert_image(img_rect, filename=str(sign_img_path), keep_proportion=True)
            text_rect = fitz.Rect(sign_rect.x0 + 86, sign_rect.y0 + 8, sign_rect.x1 - 6, sign_rect.y1 - 6)
        else:
            text_rect = fitz.Rect(sign_rect.x0 + 8, sign_rect.y0 + 8, sign_rect.x1 - 8, sign_rect.y1 - 8)

        page.insert_textbox(
            text_rect,
            signature_text,
            fontsize=9,
            fontname="helv",
            color=(0.05, 0.2, 0.35),
            align=0,
        )

        doc.save(str(output_path), garbage=3, deflate=True)
        doc.close()

        cleanup_paths = [input_path, output_path]
        if sign_img_path:
            cleanup_paths.append(sign_img_path)

        queue_cleanup(cleanup_paths)
        return send_file(str(output_path), as_attachment=True, download_name=f"{secure_filename(stem)}_signed.pdf")
    except Exception as exc:
        return template_error(f"Falha ao assinar PDF: {exc}", 500)


@app.post("/tools/remove-watermark")
def remove_watermark():
    uploaded = request.files.get("watermark_file")
    watermark_text = (request.form.get("watermark_text") or "").strip()

    if not uploaded or not uploaded.filename.lower().endswith(".pdf"):
        return template_error("Envie um PDF valido para remover marca de agua.")
    if not watermark_text:
        return template_error("Indique o texto da marca de agua a remover.")

    stem = Path(uploaded.filename).stem
    input_path = UPLOAD_DIR / unique_name(stem, ".pdf")
    output_path = OUTPUT_DIR / unique_name(f"{stem}_no_watermark", ".pdf")
    uploaded.save(input_path)

    try:
        doc = fitz.open(str(input_path))
        found = 0
        for page in doc:
            areas = page.search_for(watermark_text)
            for rect in areas:
                page.add_redact_annot(rect, fill=(1, 1, 1))
                found += 1
            if areas:
                page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)

        if found == 0:
            doc.close()
            return template_error("Nao encontrei essa marca de agua no documento.")

        doc.save(str(output_path), garbage=4, deflate=True, clean=True)
        doc.close()

        queue_cleanup([input_path, output_path])
        return send_file(str(output_path), as_attachment=True, download_name=f"{secure_filename(stem)}_no_watermark.pdf")
    except Exception as exc:
        return template_error(f"Falha ao remover marca de agua: {exc}", 500)


@app.post("/tools/remove-password")
def remove_password_document():
    uploaded = request.files.get("remove_pass_file")
    password = (request.form.get("remove_pass_value") or "").strip()

    if not uploaded or not uploaded.filename.lower().endswith(".pdf"):
        return template_error("Envie um PDF valido para remover password.")

    stem = Path(uploaded.filename).stem
    input_path = UPLOAD_DIR / unique_name(stem, ".pdf")
    output_path = OUTPUT_DIR / unique_name(f"{stem}_no_password", ".pdf")
    uploaded.save(input_path)

    try:
        reader = PdfReader(str(input_path))
        if reader.is_encrypted:
            if not password:
                return template_error("Este PDF esta protegido. Indique a password atual.")
            decrypt_result = reader.decrypt(password)
            if decrypt_result == 0:
                return template_error("Password invalida para este PDF.", 403)

        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)

        with output_path.open("wb") as out_file:
            writer.write(out_file)

        queue_cleanup([input_path, output_path])
        return send_file(str(output_path), as_attachment=True, download_name=f"{secure_filename(stem)}_no_password.pdf")
    except Exception as exc:
        return template_error(f"Falha ao remover password: {exc}", 500)


@app.post("/tools/ocr")
def ocr_extract():
    uploaded = request.files.get("ocr_file")
    if not uploaded or not uploaded.filename:
        return template_error("Envie um PDF ou imagem para OCR.")

    filename = uploaded.filename.lower()
    stem = Path(uploaded.filename).stem
    ext = Path(uploaded.filename).suffix.lower()
    input_path = UPLOAD_DIR / unique_name(stem, ext)
    output_path = OUTPUT_DIR / unique_name(f"{stem}_ocr", ".txt")
    uploaded.save(input_path)

    language = (request.form.get("ocr_lang") or "por").strip() or "por"

    try:
        extracted_parts: list[str] = []

        if ext == ".pdf":
            doc = fitz.open(str(input_path))
            for i, page in enumerate(doc, start=1):
                text = page.get_text("text")
                if text and text.strip():
                    extracted_parts.append(f"\n--- PÃ¡gina {i} ---\n{text}")
                elif TESSERACT_AVAILABLE:
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                    img_path = TEMP_DIR / unique_name(f"ocr_page_{i}", ".png")
                    pix.save(str(img_path))
                    with Image.open(img_path) as img:
                        ocr_text = pytesseract.image_to_string(img, lang=language)
                    extracted_parts.append(f"\n--- PÃ¡gina {i} (OCR) ---\n{ocr_text}")
                    img_path.unlink(missing_ok=True)
            doc.close()
        elif ext in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"}:
            if not TESSERACT_AVAILABLE:
                return template_error("OCR para imagem requer Tesseract instalado no servidor.", 500)
            with Image.open(input_path) as img:
                extracted_parts.append(pytesseract.image_to_string(img, lang=language))
        else:
            return template_error("Formato invÃ¡lido para OCR. Use PDF ou imagem.")

        text_out = "\n".join(extracted_parts).strip()
        if not text_out:
            text_out = "Nenhum texto detetado no ficheiro."

        output_path.write_text(text_out, encoding="utf-8")

        queue_cleanup([input_path, output_path])
        return send_file(str(output_path), as_attachment=True, download_name=f"{secure_filename(stem)}_ocr.txt")
    except Exception as exc:
        return template_error(f"Falha no OCR/extraÃ§Ã£o de texto: {exc}", 500)


@app.post("/tools/transcribe-audio")
def transcribe_audio():
    uploaded = request.files.get("audio_file")
    lang = (request.form.get("audio_lang") or "pt-PT").strip() or "pt-PT"

    if not uploaded or not uploaded.filename:
        return template_error("Envie um ficheiro de audio ou video para transcrever.")

    ext = Path(uploaded.filename).suffix.lower()
    if ext not in {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".mp4", ".webm", ".mov"}:
        return template_error("Formato nao suportado para transcricao.")
    if AudioSegment is None or sr is None:
        return template_error("Transcricao indisponivel: instale pydub e SpeechRecognition no servidor.", 500)

    stem = Path(uploaded.filename).stem
    input_path = RUNTIME_DIR / unique_name(stem, ext)
    wav_dir = RUNTIME_DIR / unique_name("transcribe_chunks", "")
    output_path = OUTPUT_DIR / unique_name(f"{stem}_transcricao", ".txt")
    wav_dir.mkdir(parents=True, exist_ok=True)
    uploaded.save(input_path)

    try:
        for key in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "all_proxy"):
            os.environ.pop(key, None)
        os.environ["NO_PROXY"] = "*"
        os.environ["no_proxy"] = "*"

        audio = AudioSegment.from_file(input_path)
        recognizer = sr.Recognizer()
        chunk_ms = 45000
        texts: list[str] = []

        idx = 1
        for start in range(0, len(audio), chunk_ms):
            chunk = audio[start : start + chunk_ms]
            wav_path = wav_dir / f"chunk_{idx}.wav"
            chunk.export(wav_path, format="wav")

            with sr.AudioFile(str(wav_path)) as source:
                data = recognizer.record(source)
            try:
                text = recognizer.recognize_google(data, language=lang)
            except sr.UnknownValueError:
                text = ""
            except sr.RequestError as req_err:
                return template_error(f"Falha no servico de transcricao: {req_err}", 502)

            texts.append(text)
            idx += 1

        transcript = "\n".join(part for part in texts if part.strip()).strip()
        if not transcript:
            transcript = "Nao foi possivel transcrever audio reconhecivel."

        output_path.write_text(transcript, encoding="utf-8")
        queue_cleanup([input_path, output_path], [wav_dir])
        return send_file(str(output_path), as_attachment=True, download_name=f"{secure_filename(stem)}_transcricao.txt")
    except Exception as exc:
        return template_error(f"Falha ao transcrever audio: {exc}", 500)


@app.post("/tools/translate")
def translate_document():
    uploaded = request.files.get("translate_file")
    if not uploaded or not uploaded.filename:
        return template_error("Envie um ficheiro para traduzir (DOCX, PDF ou TXT).")

    source_lang = (request.form.get("tr_source") or "auto").strip() or "auto"
    target_lang = (request.form.get("tr_target") or "pt").strip() or "pt"

    stem = Path(uploaded.filename).stem
    ext = Path(uploaded.filename).suffix.lower()
    input_path = UPLOAD_DIR / unique_name(stem, ext)
    uploaded.save(input_path)

    try:
        for key in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "all_proxy"):
            os.environ.pop(key, None)
        os.environ["NO_PROXY"] = "*"
        os.environ["no_proxy"] = "*"

        if ext == ".docx":
            output_path = OUTPUT_DIR / unique_name(f"{stem}_{target_lang}", ".docx")
            shutil.copy2(input_path, output_path)
            translate_docx(output_path, source_lang, target_lang)
            queue_cleanup([input_path, output_path])
            return send_file(str(output_path), as_attachment=True, download_name=f"{secure_filename(stem)}_{target_lang}.docx")

        if ext == ".pdf":
            docx_path = OUTPUT_DIR / unique_name(f"{stem}_translated", ".docx")
            cv = Converter(str(input_path))
            cv.convert(str(docx_path))
            cv.close()
            translate_docx(docx_path, source_lang, target_lang)
            queue_cleanup([input_path, docx_path])
            return send_file(str(docx_path), as_attachment=True, download_name=f"{secure_filename(stem)}_{target_lang}.docx")

        if ext == ".txt":
            output_path = OUTPUT_DIR / unique_name(f"{stem}_{target_lang}", ".txt")
            translator = GoogleTranslator(source=source_lang, target=target_lang)
            source_text = input_path.read_text(encoding="utf-8", errors="ignore")
            translated = translator.translate(source_text)
            output_path.write_text(translated or "", encoding="utf-8")
            queue_cleanup([input_path, output_path])
            return send_file(str(output_path), as_attachment=True, download_name=f"{secure_filename(stem)}_{target_lang}.txt")

        return template_error("Formato nÃ£o suportado. Use DOCX, PDF ou TXT.")
    except Exception as exc:
        return template_error(f"Falha na traduÃ§Ã£o de documento: {exc}", 500)


@app.post("/tools/youtube-to-mp3")
def youtube_to_mp3():
    url = (request.form.get("youtube_url") or "").strip()
    if not url:
        return template_error("Indique um link de YouTube.")
    if yt_dlp is None:
        return template_error("YouTube indisponivel: instale yt-dlp no servidor.", 500)
    if not FFMPEG_PATH:
        return template_error("ffmpeg nao encontrado no servidor. Necessario para MP3.", 500)

    work_dir = RUNTIME_DIR / unique_name("yt_mp3", "")
    work_dir.mkdir(parents=True, exist_ok=True)
    out_template = str(work_dir / "%(title)s [%(id)s].%(ext)s")
    expected_mp3 = None
    video_title = ""

    try:
        opts = build_ytdlp_opts(out_template, "bestaudio/best", playlist=False, extract_mp3=True)
        info, prepared = ytdlp_extract_with_fallback(url, opts)
        video_title = info.get("title") or ""
        expected_mp3 = prepared.with_suffix(".mp3")

        if not expected_mp3 or not expected_mp3.exists():
            matches = sorted(work_dir.glob("*.mp3"), key=lambda p: p.stat().st_mtime, reverse=True)
            if not matches:
                return template_error("Nao foi possivel gerar MP3 para este link.", 500)
            expected_mp3 = matches[0]

        queue_cleanup([expected_mp3], [work_dir])
        download_name = safe_download_name(video_title, ".mp3", expected_mp3.stem)
        return send_file(str(expected_mp3), as_attachment=True, download_name=download_name)
    except Exception as exc:
        return template_error(ytdlp_user_message("Falha em YouTube para MP3", exc), 500)


@app.post("/tools/youtube-to-mp4")
def youtube_to_mp4():
    url = (request.form.get("youtube_url_mp4") or "").strip()
    if not url:
        return template_error("Indique um link de YouTube.")
    if yt_dlp is None:
        return template_error("YouTube indisponivel: instale yt-dlp no servidor.", 500)

    work_dir = RUNTIME_DIR / unique_name("yt_mp4", "")
    work_dir.mkdir(parents=True, exist_ok=True)
    out_template = str(work_dir / "%(title)s [%(id)s].%(ext)s")
    expected_mp4 = None
    video_title = ""

    try:
        opts = build_ytdlp_opts(out_template, "bestvideo+bestaudio/best", playlist=False, extract_mp3=False)
        opts["merge_output_format"] = "mp4"
        info, prepared = ytdlp_extract_with_fallback(url, opts)
        video_title = info.get("title") or ""
        expected_mp4 = prepared.with_suffix(".mp4")

        if not expected_mp4 or not expected_mp4.exists():
            matches = sorted(work_dir.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
            if not matches:
                return template_error("Nao foi possivel gerar MP4 para este link.", 500)
            expected_mp4 = matches[0]

        queue_cleanup([expected_mp4], [work_dir])
        download_name = safe_download_name(video_title, ".mp4", expected_mp4.stem)
        return send_file(str(expected_mp4), as_attachment=True, download_name=download_name)
    except Exception as exc:
        return template_error(ytdlp_user_message("Falha em YouTube para MP4", exc), 500)


@app.post("/tools/youtube-playlist-to-mp3")
def youtube_playlist_to_mp3():
    url = (request.form.get("youtube_playlist_url_mp3") or "").strip()
    if not url:
        return template_error("Indique um link de playlist do YouTube.")
    if yt_dlp is None:
        return template_error("YouTube indisponivel: instale yt-dlp no servidor.", 500)
    if not FFMPEG_PATH:
        return template_error("ffmpeg nao encontrado no servidor. Necessario para MP3.", 500)

    work_dir = RUNTIME_DIR / unique_name("yt_playlist_mp3", "")
    work_dir.mkdir(parents=True, exist_ok=True)
    out_template = str(work_dir / "%(playlist_index)03d - %(title)s [%(id)s].%(ext)s")
    playlist_title = "youtube_playlist_mp3"
    zip_path = OUTPUT_DIR / unique_name("youtube_playlist_mp3", ".zip")

    try:
        opts = build_ytdlp_opts(out_template, "bestaudio/best", playlist=True, extract_mp3=True)
        info, _ = ytdlp_extract_with_fallback(url, opts)
        playlist_title = info.get("title") or playlist_title

        files = sorted(work_dir.glob("*.mp3"))
        if not files:
            return template_error("Nao foi possivel gerar MP3 para esta playlist.", 500)

        zip_files(files, zip_path)
        queue_cleanup([zip_path], [work_dir])
        return send_file(
            str(zip_path),
            as_attachment=True,
            download_name=safe_download_name(playlist_title, ".zip", "youtube_playlist_mp3"),
        )
    except Exception as exc:
        return template_error(ytdlp_user_message("Falha em playlist YouTube para MP3", exc), 500)


@app.post("/tools/youtube-playlist-to-mp4")
def youtube_playlist_to_mp4():
    url = (request.form.get("youtube_playlist_url_mp4") or "").strip()
    if not url:
        return template_error("Indique um link de playlist do YouTube.")
    if yt_dlp is None:
        return template_error("YouTube indisponivel: instale yt-dlp no servidor.", 500)

    work_dir = RUNTIME_DIR / unique_name("yt_playlist_mp4", "")
    work_dir.mkdir(parents=True, exist_ok=True)
    out_template = str(work_dir / "%(playlist_index)03d - %(title)s [%(id)s].%(ext)s")
    playlist_title = "youtube_playlist_mp4"
    zip_path = OUTPUT_DIR / unique_name("youtube_playlist_mp4", ".zip")

    try:
        opts = build_ytdlp_opts(out_template, "bestvideo+bestaudio/best", playlist=True, extract_mp3=False)
        opts["merge_output_format"] = "mp4"
        info, _ = ytdlp_extract_with_fallback(url, opts)
        playlist_title = info.get("title") or playlist_title

        files = sorted(work_dir.glob("*.mp4"))
        if not files:
            return template_error("Nao foi possivel gerar MP4 para esta playlist.", 500)

        zip_files(files, zip_path)
        queue_cleanup([zip_path], [work_dir])
        return send_file(
            str(zip_path),
            as_attachment=True,
            download_name=safe_download_name(playlist_title, ".zip", "youtube_playlist_mp4"),
        )
    except Exception as exc:
        return template_error(ytdlp_user_message("Falha em playlist YouTube para MP4", exc), 500)


@app.post("/tools/spotify-to-mp3")
def spotify_to_mp3():
    url = (request.form.get("spotify_url") or "").strip()
    if not url:
        return template_error("Indique um link de Spotify.")

    work_dir = RUNTIME_DIR / unique_name("spotify_dl", "")
    work_dir.mkdir(parents=True, exist_ok=True)

    try:
        cmd = [
            "python",
            "-m",
            "spotdl",
            url,
            "--output",
            str(work_dir),
            "--path-template",
            "{title}.{ext}",
            "--output-format",
            "mp3",
            "--ffmpeg",
            FFMPEG_PATH or "ffmpeg",
        ]
        env = os.environ.copy()
        for key in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "all_proxy"):
            env.pop(key, None)
        env["NO_PROXY"] = "*"
        env["no_proxy"] = "*"
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600, env=env)
        if proc.returncode != 0:
            msg = (proc.stderr or proc.stdout or "Erro desconhecido no spotdl.").strip()
            return template_error(f"Falha em Spotify para MP3: {msg}", 500)

        mp3_files = sorted(work_dir.glob("*.mp3"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not mp3_files:
            return template_error("Nao foi gerado MP3 para este link de Spotify.", 500)

        result_path = mp3_files[0]
        queue_cleanup([result_path], [work_dir])
        download_name = safe_download_name(result_path.stem, ".mp3", "spotify_audio")
        return send_file(str(result_path), as_attachment=True, download_name=download_name)
    except subprocess.TimeoutExpired:
        return template_error("Tempo limite excedido no download do Spotify.", 504)
    except Exception as exc:
        return template_error(f"Falha em Spotify para MP3: {exc}", 500)


@app.post("/tools/spotify-playlist-to-mp3")
def spotify_playlist_to_mp3():
    url = (request.form.get("spotify_playlist_url") or "").strip()
    if not url:
        return template_error("Indique um link de playlist do Spotify.")

    work_dir = RUNTIME_DIR / unique_name("spotify_playlist_dl", "")
    work_dir.mkdir(parents=True, exist_ok=True)
    zip_path = OUTPUT_DIR / unique_name("spotify_playlist_mp3", ".zip")

    try:
        cmd = [
            "python",
            "-m",
            "spotdl",
            url,
            "--output",
            str(work_dir),
            "--path-template",
            "{artists} - {title}.{ext}",
            "--output-format",
            "mp3",
            "--ffmpeg",
            FFMPEG_PATH or "ffmpeg",
        ]
        env = os.environ.copy()
        for key in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "all_proxy"):
            env.pop(key, None)
        env["NO_PROXY"] = "*"
        env["no_proxy"] = "*"
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=1800, env=env)
        if proc.returncode != 0:
            msg = (proc.stderr or proc.stdout or "Erro desconhecido no spotdl.").strip()
            return template_error(f"Falha em playlist Spotify para MP3: {msg}", 500)

        files = sorted(work_dir.glob("*.mp3"))
        if not files:
            return template_error("Nao foi gerado MP3 para esta playlist do Spotify.", 500)

        zip_files(files, zip_path)
        queue_cleanup([zip_path], [work_dir])
        return send_file(str(zip_path), as_attachment=True, download_name="spotify_playlist_mp3.zip")
    except subprocess.TimeoutExpired:
        return template_error("Tempo limite excedido no download da playlist Spotify.", 504)
    except Exception as exc:
        return template_error(f"Falha em playlist Spotify para MP3: {exc}", 500)


@app.errorhandler(413)
def file_too_large(_):
    return template_error(f"Ficheiro demasiado grande. Limite atual: {MAX_UPLOAD_MB}MB.", 413)


@app.get("/healthz")
def healthz():
    return {
        "status": "ok",
        "app_version": APP_VERSION,
        "max_upload_mb": MAX_UPLOAD_MB,
    }, 200


@app.get("/readyz")
def readyz():
    return {
        "status": "ready",
        "services": {
            "tesseract": TESSERACT_AVAILABLE,
            "ffmpeg": bool(FFMPEG_PATH),
            "libreoffice": bool(LIBREOFFICE_PATH),
            "yt_dlp": yt_dlp is not None,
            "speech_recognition": sr is not None,
            "audio_segment": AudioSegment is not None,
        },
    }, 200


@app.errorhandler(404)
def page_not_found(_):
    return template_error("Página não encontrada.", 404)


@app.errorhandler(500)
def internal_error(_):
    return template_error("Erro interno temporário. Tenta novamente em instantes.", 500)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)
