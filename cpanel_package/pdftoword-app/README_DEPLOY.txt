DEPLOY RAPIDO - cPanel (sem comandos)

1) No cPanel File Manager, abre public_html
2) Cria a pasta: pdftoword-app
3) Faz upload de TODOS os ficheiros deste pacote para public_html/pdftoword-app
4) Abre public_html/pdftoword-app/config.php
5) Altera:
   $TARGET_APP_URL = "https://SEU-SERVICO.onrender.com";
   para a tua URL real do Render
6) Guarda
7) Acede:
   https://freetools4all.duckdns.org/pdftoword-app/

Notas:
- MODE = "redirect" -> abre direto no Render
- MODE = "embed" -> abre em iframe dentro do teu dominio
- Se quiseres pagina temporaria, usa:
  $MAINTENANCE_MODE = true;
- Para anuncios:
  editar index.php e colar scripts nas zonas "Espaco para Anuncio (Topo/Rodape)".
- Paginas legais incluidas:
  terms.php, privacy.php, cookies.php
