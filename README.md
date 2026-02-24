# PDF to Word Web

Aplicação web para converter PDF para DOCX com tradução opcional.

## Executar localmente

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python web_app.py
```

Abrir: `http://localhost:5000`

## Publicar

Este projeto inclui `Procfile` e duas opções de dependências:

- `requirements-server.txt` (recomendado): versão mais leve e compatível para servidor.
- `requirements.txt`: versão completa com ferramentas extras (YouTube/Spotify/transcrição).

### Linux + Apache (rápido)

No diretório do projeto no servidor:

```bash
sudo bash install_linux_apache.sh --domain _
```

Use o teu domínio no lugar de `_` quando já estiver apontado para o servidor.

## Operação e monetização

- `GET /healthz`: estado base da aplicação.
- `GET /readyz`: estado dos serviços opcionais (tesseract/ffmpeg/libreoffice/yt-dlp).
- `POST /convert`: alias legacy para PDF -> Word (compatibilidade com páginas antigas).
- Workflow `.github/workflows/keepalive-ping.yml`: ping automático 10/10 min (GitHub Actions).

Variáveis de ambiente novas:

- `MAX_UPLOAD_MB` (default: `40`)
- `ADSENSE_CLIENT` (ex: `ca-pub-xxxxxxxxxxxxxxxx`)
- `ADSENSE_SLOT_TOP` (opcional)
- `ADSENSE_SLOT_INLINE` (opcional)
- `APP_VERSION` (opcional)
- `HEALTHCHECK_URL` (GitHub Secret para o workflow de ping, ex: `https://<app>.onrender.com/healthz`)
- `YTDLP_PLAYER_CLIENTS` (default: `android,web`)
- `YTDLP_VISITOR_DATA` (opcional)
- `YTDLP_PO_TOKEN` (opcional)
- `YTDLP_USER_AGENT` (opcional)

Validação rápida de rotas:

```powershell
python scripts\smoke_validate_routes.py
```
