$ErrorActionPreference = "Stop"
$base = "http://127.0.0.1:5000"
$td = Join-Path (Get-Location) (".test_artifacts_" + (Get-Date -Format "yyyyMMdd_HHmmss"))
New-Item -ItemType Directory -Path $td | Out-Null

function Test-Endpoint {
  param(
    [string]$Name,
    [string]$Command,
    [string]$OutputPath = ""
  )
  try {
    $code = Invoke-Expression $Command
    $ok = $false
    if ($code -eq "200") {
      if ($OutputPath -and (Test-Path $OutputPath)) {
        $size = (Get-Item $OutputPath).Length
        $ok = $size -gt 0
      } else {
        $ok = $true
      }
    }
    [PSCustomObject]@{ Feature=$Name; Code=$code; Pass=$ok; Output=$OutputPath }
  } catch {
    [PSCustomObject]@{ Feature=$Name; Code="ERR"; Pass=$false; Output=$_.Exception.Message }
  }
}

"Hello world. This is a translation test." | Set-Content -Path (Join-Path $td "sample.txt") -Encoding UTF8

@"
import wave, struct, math
fr=16000
dur=2
amp=12000
f=440
with wave.open(r'$td\\tone.wav','w') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(fr)
    for i in range(fr*dur):
        v=int(amp*math.sin(2*math.pi*f*i/fr))
        w.writeframes(struct.pack('<h', v))
"@ | python -

@"
import fitz
p=fitz.open()
pg=p.new_page()
pg.insert_text((72,72),'CONFIDENTIAL',fontsize=36,color=(0.8,0.8,0.8))
pg.insert_text((72,140),'Body text for watermark test',fontsize=12)
p.save(r'$td\\watermark_sample.pdf')
"@ | python -

$results = @()

$results += Test-Endpoint "01 PDF to Word" "curl.exe -s -o '$td\\pdf_to_word.docx' -w '%{http_code}' -F '_tool=pdf-to-word' -F 'pdf_file=@CvEN11318.pdf' $base/tools/pdf-to-word" "$td\\pdf_to_word.docx"
$results += Test-Endpoint "02 Word to PDF" "curl.exe -s -o '$td\\word_to_pdf.pdf' -w '%{http_code}' -F '_tool=word-to-pdf' -F 'word_file=@CvEN11318_PT.docx' $base/tools/word-to-pdf" "$td\\word_to_pdf.pdf"
$results += Test-Endpoint "03 PDF to Images" "curl.exe -s -o '$td\\pdf_images.zip' -w '%{http_code}' -F '_tool=pdf-to-images' -F 'pdf_file_images=@CvEN11318.pdf' -F 'scale=1.2' $base/tools/pdf-to-images" "$td\\pdf_images.zip"

if (Test-Path "$td\\pdf_images.zip") { Expand-Archive -Path "$td\\pdf_images.zip" -DestinationPath "$td\\imgs" -Force }
$img1 = Get-ChildItem "$td\\imgs" -Filter *.png | Select-Object -First 1
if ($img1) {
  $results += Test-Endpoint "04 Images to PDF" "curl.exe -s -o '$td\\images_to_pdf.pdf' -w '%{http_code}' -F '_tool=images-to-pdf' -F 'image_files=@$($img1.FullName)' $base/tools/images-to-pdf" "$td\\images_to_pdf.pdf"
} else {
  $results += [PSCustomObject]@{ Feature="04 Images to PDF"; Code="SKIP"; Pass=$false; Output="No image extracted" }
}

$results += Test-Endpoint "05 Merge PDFs" "curl.exe -s -o '$td\\merge.pdf' -w '%{http_code}' -F '_tool=merge-pdf' -F 'merge_files=@CvEN11318.pdf' -F 'merge_files=@CvEN11318.pdf' $base/tools/merge-pdf" "$td\\merge.pdf"
$results += Test-Endpoint "06 Split PDF" "curl.exe -s -o '$td\\split.pdf' -w '%{http_code}' -F '_tool=split-pdf' -F 'split_file=@CvEN11318.pdf' -F 'split_mode=range' -F 'start_page=1' -F 'end_page=2' $base/tools/split-pdf" "$td\\split.pdf"
$results += Test-Endpoint "07 Compress PDF" "curl.exe -s -o '$td\\compressed.pdf' -w '%{http_code}' -F '_tool=compress-pdf' -F 'compress_file=@CvEN11318.pdf' $base/tools/compress-pdf" "$td\\compressed.pdf"
$results += Test-Endpoint "08 Protect PDF" "curl.exe -s -o '$td\\protected.pdf' -w '%{http_code}' -F '_tool=protect-pdf' -F 'protect_file=@CvEN11318.pdf' -F 'password=Test123!' $base/tools/protect-pdf" "$td\\protected.pdf"
$results += Test-Endpoint "09 Unlock PDF" "curl.exe -s -o '$td\\unlocked.pdf' -w '%{http_code}' -F '_tool=unlock-pdf' -F 'unlock_file=@$td\\protected.pdf' -F 'unlock_password=Test123!' $base/tools/unlock-pdf" "$td\\unlocked.pdf"
$results += Test-Endpoint "10 Sign PDF" "curl.exe -s -o '$td\\signed.pdf' -w '%{http_code}' -F '_tool=sign-pdf' -F 'sign_file=@CvEN11318.pdf' -F 'signature_text=Signed by QA' -F 'signature_page=last' $base/tools/sign-pdf" "$td\\signed.pdf"
$results += Test-Endpoint "11 Remove Watermark" "curl.exe -s -o '$td\\watermark_removed.pdf' -w '%{http_code}' -F '_tool=remove-watermark' -F 'watermark_file=@$td\\watermark_sample.pdf' -F 'watermark_text=CONFIDENTIAL' $base/tools/remove-watermark" "$td\\watermark_removed.pdf"
$results += Test-Endpoint "12 Remove Password" "curl.exe -s -o '$td\\no_password.pdf' -w '%{http_code}' -F '_tool=remove-password' -F 'remove_pass_file=@$td\\protected.pdf' -F 'remove_pass_value=Test123!' $base/tools/remove-password" "$td\\no_password.pdf"
$results += Test-Endpoint "13 OCR" "curl.exe -s -o '$td\\ocr.txt' -w '%{http_code}' -F '_tool=ocr' -F 'ocr_file=@CvEN11318.pdf' -F 'ocr_lang=eng' $base/tools/ocr" "$td\\ocr.txt"
$results += Test-Endpoint "14 Translate Document" "curl.exe -s -o '$td\\translated.txt' -w '%{http_code}' -F '_tool=translate' -F 'translate_file=@$td\\sample.txt' -F 'tr_source=en' -F 'tr_target=pt' $base/tools/translate" "$td\\translated.txt"
$results += Test-Endpoint "15 Transcribe Audio to TXT" "curl.exe -s -o '$td\\transcribed.txt' -w '%{http_code}' -F '_tool=transcribe-audio' -F 'audio_file=@$td\\tone.wav' -F 'audio_lang=en-US' $base/tools/transcribe-audio" "$td\\transcribed.txt"
$results += Test-Endpoint "16 YouTube to MP3" "curl.exe -s -o '$td\\youtube_mp3.bin' -w '%{http_code}' -X POST -d '_tool=youtube-to-mp3' --data-urlencode 'youtube_url=https://www.youtube.com/watch?v=dQw4w9WgXcQ' $base/tools/youtube-to-mp3" "$td\\youtube_mp3.bin"
$results += Test-Endpoint "17 YouTube to MP4" "curl.exe -s -o '$td\\youtube_mp4.bin' -w '%{http_code}' -X POST -d '_tool=youtube-to-mp4' --data-urlencode 'youtube_url_mp4=https://www.youtube.com/watch?v=dQw4w9WgXcQ' $base/tools/youtube-to-mp4" "$td\\youtube_mp4.bin"
$results += Test-Endpoint "18 YouTube Playlist to MP3" "curl.exe -s -o '$td\\yt_playlist_mp3.zip' -w '%{http_code}' -X POST -d '_tool=youtube-playlist-to-mp3' --data-urlencode 'youtube_playlist_url_mp3=ytsearch2:never gonna give you up' $base/tools/youtube-playlist-to-mp3" "$td\\yt_playlist_mp3.zip"
$results += Test-Endpoint "19 YouTube Playlist to MP4" "curl.exe -s -o '$td\\yt_playlist_mp4.zip' -w '%{http_code}' -X POST -d '_tool=youtube-playlist-to-mp4' --data-urlencode 'youtube_playlist_url_mp4=ytsearch2:never gonna give you up' $base/tools/youtube-playlist-to-mp4" "$td\\yt_playlist_mp4.zip"
$results += Test-Endpoint "20 Spotify to MP3" "curl.exe -s -o '$td\\spotify_mp3.bin' -w '%{http_code}' -X POST -d '_tool=spotify-to-mp3' --data-urlencode 'spotify_url=https://open.spotify.com/track/11dFghVXANMlKmJXsNCbNl' $base/tools/spotify-to-mp3" "$td\\spotify_mp3.bin"
$results += Test-Endpoint "21 Spotify Playlist to MP3" "curl.exe -s -o '$td\\spotify_playlist.zip' -w '%{http_code}' -X POST -d '_tool=spotify-playlist-to-mp3' --data-urlencode 'spotify_playlist_url=https://open.spotify.com/track/11dFghVXANMlKmJXsNCbNl' $base/tools/spotify-playlist-to-mp3" "$td\\spotify_playlist.zip"

$results | ConvertTo-Json -Depth 5 | Set-Content -Path "$td\\report.json" -Encoding UTF8
Get-Content "$td\\report.json"
