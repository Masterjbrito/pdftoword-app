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
