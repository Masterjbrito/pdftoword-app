<?php
require_once __DIR__ . '/config.php';

$target = trim((string)($TARGET_APP_URL ?? ''));
$mode = strtolower(trim((string)($MODE ?? 'redirect')));
$maintenance = (bool)($MAINTENANCE_MODE ?? false);
$siteName = trim((string)($SITE_NAME ?? 'PDF to Word'));
$siteDomain = trim((string)($SITE_DOMAIN ?? ''));
$contactEmail = trim((string)($CONTACT_EMAIL ?? ''));

if ($maintenance || $target === '' || stripos($target, 'SEU-SERVICO.onrender.com') !== false) {
    http_response_code(503);
    ?>
<!doctype html>
<html lang="pt">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PDF to Word - Em configuracao</title>
  <style>
    body{font-family:Arial,sans-serif;background:#f5f7fb;color:#1a1f2e;margin:0;display:grid;place-items:center;min-height:100vh}
    .card{max-width:680px;background:#fff;border:1px solid #dbe3f0;border-radius:12px;padding:28px;box-shadow:0 12px 35px rgba(6,27,72,.08)}
    h1{margin:0 0 12px 0;font-size:26px}
    p{margin:8px 0;line-height:1.5}
    code{background:#eef3fb;border:1px solid #dbe3f0;padding:2px 6px;border-radius:6px}
  </style>
</head>
<body>
  <div class="card">
    <h1>Aplicacao em configuracao</h1>
    <p>O destino Render ainda nao foi configurado neste pacote.</p>
    <p>Edita o ficheiro <code>config.php</code> e altera <code>$TARGET_APP_URL</code> para a tua URL <code>onrender.com</code>.</p>
    <p>Depois recarrega esta pagina.</p>
  </div>
</body>
</html>
<?php
    exit;
}

$target = rtrim($target, '/');

if ($mode === 'embed') {
    ?>
<!doctype html>
<html lang="pt">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title><?php echo htmlspecialchars($siteName, ENT_QUOTES, 'UTF-8'); ?></title>
  <meta name="description" content="Ferramentas online para PDF e documentos. Conversao de PDF para Word com interface simples e rapida.">
  <link rel="stylesheet" href="assets/styles.css">
</head>
<body>
  <header class="topbar">
    <div class="wrap">
      <h1><?php echo htmlspecialchars($siteName, ENT_QUOTES, 'UTF-8'); ?></h1>
      <p>Plataforma online para converter e gerir documentos de forma simples, sem instalar programas no computador.</p>
    </div>
  </header>

  <main class="wrap content">
    <section class="panel">
      <h2>Como funciona</h2>
      <p>Carrega o ficheiro, escolhe a ferramenta e descarrega o resultado. O processamento e feito de forma automatica para simplificar o uso no dia a dia.</p>
    </section>

    <section class="ad-slot" aria-label="Publicidade topo">
      <div class="ad-label">Espaco para Anuncio (Topo)</div>
      <div class="ad-box">
        <!-- Inserir aqui o script do anuncio (ex: Google AdSense) -->
      </div>
    </section>

    <section class="app-frame panel">
      <h2>Dashboard</h2>
      <iframe src="<?php echo htmlspecialchars($target, ENT_QUOTES, 'UTF-8'); ?>" allow="clipboard-read; clipboard-write"></iframe>
    </section>

    <section class="ad-slot" aria-label="Publicidade rodape">
      <div class="ad-label">Espaco para Anuncio (Rodape)</div>
      <div class="ad-box">
        <!-- Inserir aqui o script do anuncio (ex: Google AdSense) -->
      </div>
    </section>
  </main>

  <footer class="footer">
    <div class="wrap">
      <p>Informacao legal: ao utilizar este servico, concordas com os nossos termos e politica de privacidade.</p>
      <p>
        <a href="terms.php">Termos</a> |
        <a href="privacy.php">Privacidade</a> |
        <a href="cookies.php">Cookies</a>
      </p>
      <p>
        Dominio: <?php echo htmlspecialchars($siteDomain, ENT_QUOTES, 'UTF-8'); ?>
        <?php if ($contactEmail !== ''): ?>
          | Contacto: <a href="mailto:<?php echo htmlspecialchars($contactEmail, ENT_QUOTES, 'UTF-8'); ?>"><?php echo htmlspecialchars($contactEmail, ENT_QUOTES, 'UTF-8'); ?></a>
        <?php endif; ?>
      </p>
      <p>&copy; <?php echo date('Y'); ?> <?php echo htmlspecialchars($siteName, ENT_QUOTES, 'UTF-8'); ?>. Todos os direitos reservados.</p>
    </div>
  </footer>
</body>
</html>
<?php
    exit;
}

header('Location: ' . $target, true, 302);
exit;
