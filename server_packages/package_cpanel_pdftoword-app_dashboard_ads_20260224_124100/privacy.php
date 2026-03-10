<?php require_once __DIR__ . '/config.php'; ?>
<!doctype html>
<html lang="pt">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Privacidade - <?php echo htmlspecialchars($SITE_NAME, ENT_QUOTES, 'UTF-8'); ?></title>
  <link rel="stylesheet" href="assets/styles.css">
</head>
<body>
  <div class="legal">
    <h1>Politica de Privacidade</h1>
    <p>Tratamos dados tecnicos minimos para funcionamento da plataforma, seguranca e melhoria do servico.</p>
    <p>Evita enviar documentos com dados sensiveis sem necessidade. O utilizador e responsavel pelo conteudo submetido.</p>
    <p>Para contacto: <a href="mailto:<?php echo htmlspecialchars($CONTACT_EMAIL, ENT_QUOTES, 'UTF-8'); ?>"><?php echo htmlspecialchars($CONTACT_EMAIL, ENT_QUOTES, 'UTF-8'); ?></a></p>
    <p><a href="index.php">Voltar</a></p>
  </div>
</body>
</html>
