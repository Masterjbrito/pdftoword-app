<?php
require_once __DIR__ . '/config.php';

$target = trim((string)($TARGET_APP_URL ?? ''));
$mode = strtolower(trim((string)($MODE ?? 'redirect')));
$maintenance = (bool)($MAINTENANCE_MODE ?? false);

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
  <title>PDF to Word</title>
  <style>
    html,body{margin:0;padding:0;height:100%}
    iframe{border:0;width:100%;height:100%}
  </style>
</head>
<body>
  <iframe src="<?php echo htmlspecialchars($target, ENT_QUOTES, 'UTF-8'); ?>" allow="clipboard-read; clipboard-write"></iframe>
</body>
</html>
<?php
    exit;
}

header('Location: ' . $target, true, 302);
exit;
