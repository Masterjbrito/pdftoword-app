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

Este projeto já inclui `requirements.txt` e `Procfile` para deploy em serviços como Render, Railway e Heroku.
