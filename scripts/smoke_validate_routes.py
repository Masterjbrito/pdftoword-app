from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from web_app import app


GET_ROUTES = [
    "/",
    "/index",
    "/converter",
    "/converter-legacy",
    "/ferramentas",
    "/ferramentas/pdf-to-word",
    "/ferramentas/word-to-pdf",
    "/healthz",
    "/readyz",
]

POST_ROUTES = [
    "/convert",
    "/tools/pdf-to-word",
    "/tools/word-to-pdf",
    "/tools/pdf-to-images",
    "/tools/images-to-pdf",
    "/tools/merge-pdf",
    "/tools/split-pdf",
    "/tools/compress-pdf",
    "/tools/protect-pdf",
    "/tools/unlock-pdf",
    "/tools/sign-pdf",
    "/tools/remove-watermark",
    "/tools/remove-password",
    "/tools/ocr",
    "/tools/translate",
    "/tools/transcribe-audio",
    "/tools/youtube-to-mp3",
    "/tools/youtube-to-mp4",
    "/tools/youtube-playlist-to-mp3",
    "/tools/youtube-playlist-to-mp4",
    "/tools/spotify-to-mp3",
    "/tools/spotify-playlist-to-mp3",
]


def main() -> int:
    failed = False
    client = app.test_client()

    print("== GET checks ==")
    for route in GET_ROUTES:
        resp = client.get(route)
        ok = resp.status_code < 500
        print(f"{route:<35} -> {resp.status_code}")
        if not ok:
            failed = True

    print("\n== POST checks (empty payload) ==")
    for route in POST_ROUTES:
        resp = client.post(route, data={})
        ok = resp.status_code < 500
        print(f"{route:<35} -> {resp.status_code}")
        if not ok:
            failed = True

    print("\n== Summary ==")
    if failed:
        print("Smoke validation found failing endpoints (>=500).")
        return 1
    print("All checked endpoints responded without server crash.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
