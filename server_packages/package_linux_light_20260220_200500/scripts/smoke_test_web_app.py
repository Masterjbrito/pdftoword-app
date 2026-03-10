import json
import math
import os
import struct
import tempfile
import time
import wave
from pathlib import Path

import fitz
import requests


BASE_URL = os.environ.get("WEB_APP_BASE_URL", "http://127.0.0.1:5000")
TIMEOUT = int(os.environ.get("WEB_APP_TEST_TIMEOUT", "180"))


def make_tone_wav(path: Path) -> None:
    fr = 16000
    dur = 2
    amp = 12000
    freq = 440
    with wave.open(str(path), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(fr)
        for i in range(fr * dur):
            val = int(amp * math.sin(2 * math.pi * freq * i / fr))
            w.writeframes(struct.pack("<h", val))


def make_watermark_pdf(path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "CONFIDENTIAL", fontsize=32, color=(0.8, 0.8, 0.8))
    page.insert_text((72, 140), "Watermark test body", fontsize=12)
    doc.save(str(path))
    doc.close()


def is_binary_success(resp: requests.Response) -> bool:
    if resp.status_code != 200:
        return False
    if len(resp.content) == 0:
        return False
    ctype = resp.headers.get("Content-Type", "")
    # A failing response is typically HTML with error page.
    if "text/html" in ctype.lower():
        return False
    return True


def save_report(report_path: Path, results: list[dict]) -> None:
    summary = {
        "base_url": BASE_URL,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "passed": sum(1 for r in results if r["pass"]),
        "failed": sum(1 for r in results if not r["pass"]),
        "results": results,
    }
    report_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")


def run() -> int:
    root = Path.cwd()
    artifacts = root / f".smoke_{time.strftime('%Y%m%d_%H%M%S')}"
    artifacts.mkdir(parents=True, exist_ok=True)

    source_pdf = root / "CvEN11318.pdf"
    source_docx = root / "CvEN11318_PT.docx"
    sample_txt = artifacts / "sample.txt"
    tone_wav = artifacts / "tone.wav"
    wm_pdf = artifacts / "watermark_sample.pdf"
    sample_txt.write_text("Hello world. Translation smoke test.", encoding="utf-8")
    make_tone_wav(tone_wav)
    make_watermark_pdf(wm_pdf)

    results: list[dict] = []

    def record(name: str, fn):
        entry = {"feature": name, "pass": False, "status": "ERR", "detail": ""}
        try:
            ok, status, detail = fn()
            entry["pass"] = ok
            entry["status"] = status
            entry["detail"] = detail
        except Exception as exc:
            entry["detail"] = f"{type(exc).__name__}: {exc}"
        results.append(entry)

    def post_file(path: str, fields: dict, files: dict):
        return requests.post(f"{BASE_URL}{path}", data=fields, files=files, timeout=TIMEOUT)

    def post_form(path: str, fields: dict):
        return requests.post(f"{BASE_URL}{path}", data=fields, timeout=TIMEOUT)

    # Basic pages
    record("GET /", lambda: (
        (lambda r: (r.status_code == 200, str(r.status_code), "ok"))(
            requests.get(f"{BASE_URL}/", timeout=20)
        )
    ))
    record("GET /ferramentas", lambda: (
        (lambda r: (r.status_code == 200, str(r.status_code), "ok"))(
            requests.get(f"{BASE_URL}/ferramentas", timeout=20)
        )
    ))

    # Conversion and PDF tools
    record(
        "PDF to Word",
        lambda: (
            (lambda r: (is_binary_success(r), str(r.status_code), r.headers.get("Content-Type", "")))(
                post_file(
                    "/tools/pdf-to-word",
                    {"_tool": "pdf-to-word", "source_lang": "auto", "target_lang": "en"},
                    {"pdf_file": ("CvEN11318.pdf", source_pdf.open("rb"), "application/pdf")},
                )
            )
        ),
    )
    record(
        "Word to PDF",
        lambda: (
            (lambda r: (is_binary_success(r), str(r.status_code), r.text[:120] if r.status_code != 200 else "ok"))(
                post_file(
                    "/tools/word-to-pdf",
                    {"_tool": "word-to-pdf"},
                    {"word_file": ("CvEN11318_PT.docx", source_docx.open("rb"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
                )
            )
        ),
    )
    record(
        "PDF to Images",
        lambda: (
            (lambda r: (is_binary_success(r), str(r.status_code), "zip" if r.status_code == 200 else r.text[:120]))(
                post_file(
                    "/tools/pdf-to-images",
                    {"_tool": "pdf-to-images", "scale": "1.2"},
                    {"pdf_file_images": ("CvEN11318.pdf", source_pdf.open("rb"), "application/pdf")},
                )
            )
        ),
    )
    record(
        "Merge PDFs",
        lambda: (
            (lambda r: (is_binary_success(r), str(r.status_code), "ok" if r.status_code == 200 else r.text[:120]))(
                post_file(
                    "/tools/merge-pdf",
                    {"_tool": "merge-pdf"},
                    {
                        "merge_files": [
                            ("CvEN11318.pdf", source_pdf.open("rb"), "application/pdf"),
                            ("CvEN11318_copy.pdf", source_pdf.open("rb"), "application/pdf"),
                        ]
                    },
                )
            )
        ),
    )
    record(
        "Split PDF (range)",
        lambda: (
            (lambda r: (is_binary_success(r), str(r.status_code), "ok" if r.status_code == 200 else r.text[:120]))(
                post_file(
                    "/tools/split-pdf",
                    {"_tool": "split-pdf", "split_mode": "range", "start_page": "1", "end_page": "2"},
                    {"split_file": ("CvEN11318.pdf", source_pdf.open("rb"), "application/pdf")},
                )
            )
        ),
    )
    record(
        "Compress PDF",
        lambda: (
            (lambda r: (is_binary_success(r), str(r.status_code), "ok" if r.status_code == 200 else r.text[:120]))(
                post_file(
                    "/tools/compress-pdf",
                    {"_tool": "compress-pdf"},
                    {"compress_file": ("CvEN11318.pdf", source_pdf.open("rb"), "application/pdf")},
                )
            )
        ),
    )
    record(
        "Protect PDF",
        lambda: (
            (lambda r: (is_binary_success(r), str(r.status_code), "ok" if r.status_code == 200 else r.text[:120]))(
                post_file(
                    "/tools/protect-pdf",
                    {"_tool": "protect-pdf", "password": "Test123!"},
                    {"protect_file": ("CvEN11318.pdf", source_pdf.open("rb"), "application/pdf")},
                )
            )
        ),
    )
    record(
        "Sign PDF",
        lambda: (
            (lambda r: (is_binary_success(r), str(r.status_code), "ok" if r.status_code == 200 else r.text[:120]))(
                post_file(
                    "/tools/sign-pdf",
                    {"_tool": "sign-pdf", "signature_text": "Signed by Smoke Test", "signature_page": "last"},
                    {"sign_file": ("CvEN11318.pdf", source_pdf.open("rb"), "application/pdf")},
                )
            )
        ),
    )
    record(
        "Remove Watermark",
        lambda: (
            (lambda r: (is_binary_success(r), str(r.status_code), "ok" if r.status_code == 200 else r.text[:160]))(
                post_file(
                    "/tools/remove-watermark",
                    {"_tool": "remove-watermark", "watermark_text": "CONFIDENTIAL"},
                    {"watermark_file": ("watermark_sample.pdf", wm_pdf.open("rb"), "application/pdf")},
                )
            )
        ),
    )
    record(
        "OCR",
        lambda: (
            (lambda r: (is_binary_success(r), str(r.status_code), "ok" if r.status_code == 200 else r.text[:160]))(
                post_file(
                    "/tools/ocr",
                    {"_tool": "ocr", "ocr_lang": "eng"},
                    {"ocr_file": ("CvEN11318.pdf", source_pdf.open("rb"), "application/pdf")},
                )
            )
        ),
    )
    record(
        "Translate Document (txt)",
        lambda: (
            (lambda r: (is_binary_success(r), str(r.status_code), "ok" if r.status_code == 200 else r.text[:180]))(
                post_file(
                    "/tools/translate",
                    {"_tool": "translate", "tr_source": "en", "tr_target": "pt"},
                    {"translate_file": ("sample.txt", sample_txt.open("rb"), "text/plain")},
                )
            )
        ),
    )
    record(
        "Transcribe Audio to TXT",
        lambda: (
            (lambda r: (is_binary_success(r), str(r.status_code), "ok" if r.status_code == 200 else r.text[:180]))(
                post_file(
                    "/tools/transcribe-audio",
                    {"_tool": "transcribe-audio", "audio_lang": "en-US"},
                    {"audio_file": ("tone.wav", tone_wav.open("rb"), "audio/wav")},
                )
            )
        ),
    )

    # Media tools
    record(
        "YouTube to MP3",
        lambda: (
            (lambda r: (is_binary_success(r), str(r.status_code), "ok" if r.status_code == 200 else r.text[:180]))(
                post_form(
                    "/tools/youtube-to-mp3",
                    {"_tool": "youtube-to-mp3", "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
                )
            )
        ),
    )
    record(
        "YouTube to MP4",
        lambda: (
            (lambda r: (is_binary_success(r), str(r.status_code), "ok" if r.status_code == 200 else r.text[:180]))(
                post_form(
                    "/tools/youtube-to-mp4",
                    {"_tool": "youtube-to-mp4", "youtube_url_mp4": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
                )
            )
        ),
    )
    record(
        "YouTube Playlist to MP3",
        lambda: (
            (lambda r: (is_binary_success(r), str(r.status_code), "ok" if r.status_code == 200 else r.text[:180]))(
                post_form(
                    "/tools/youtube-playlist-to-mp3",
                    {"_tool": "youtube-playlist-to-mp3", "youtube_playlist_url_mp3": "ytsearch1:never gonna give you up"},
                )
            )
        ),
    )
    record(
        "YouTube Playlist to MP4",
        lambda: (
            (lambda r: (is_binary_success(r), str(r.status_code), "ok" if r.status_code == 200 else r.text[:180]))(
                post_form(
                    "/tools/youtube-playlist-to-mp4",
                    {"_tool": "youtube-playlist-to-mp4", "youtube_playlist_url_mp4": "ytsearch1:never gonna give you up"},
                )
            )
        ),
    )
    record(
        "Spotify to MP3",
        lambda: (
            (lambda r: (is_binary_success(r), str(r.status_code), "ok" if r.status_code == 200 else r.text[:220]))(
                post_form(
                    "/tools/spotify-to-mp3",
                    {"_tool": "spotify-to-mp3", "spotify_url": "https://open.spotify.com/track/11dFghVXANMlKmJXsNCbNl"},
                )
            )
        ),
    )
    record(
        "Spotify Playlist to MP3",
        lambda: (
            (lambda r: (is_binary_success(r), str(r.status_code), "ok" if r.status_code == 200 else r.text[:220]))(
                post_form(
                    "/tools/spotify-playlist-to-mp3",
                    {"_tool": "spotify-playlist-to-mp3", "spotify_playlist_url": "https://open.spotify.com/track/11dFghVXANMlKmJXsNCbNl"},
                )
            )
        ),
    )

    report_path = artifacts / "smoke_report.json"
    save_report(report_path, results)
    print(report_path)
    print(json.dumps({"passed": sum(1 for r in results if r["pass"]), "failed": sum(1 for r in results if not r["pass"])}, indent=2))
    return 0 if all(r["pass"] for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(run())
