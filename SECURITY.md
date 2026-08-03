# Segurança

## Reporte

Envie vulnerabilidades de forma privada para rodrigo@stolben.com, incluindo
impacto, passos de reprodução e versão observada. Não abra issue pública com
dados reais, credenciais ou detalhes exploráveis antes da correção.

## Escopo suportado

Somente a versão implantada mais recente recebe correções. Dependências devem
ser auditadas antes de cada release com:

    pip-audit -r requirements.txt
    python manage.py check --deploy

## Controles atuais

- isolamento dos dados de negócio por empresa;
- /admin/ global restrito a superusuários;
- CSRF, cookies seguros, HSTS, CSP, proteção contra framing e MIME sniffing;
- limite de tentativas de login e de criação de visitantes;
- tipos e tamanhos de upload restritos;
- documentos e imagens de identidade entregues por rotas autenticadas;
- geração de PDF sem busca de recursos externos;
- PostgreSQL e Redis obrigatórios no ambiente de produção.

## Operação

Mantenha TLS no proxy externo, segredo do Django e credenciais fora da imagem,
backups criptografados, logs com retenção definida, rotação de chaves e alertas
para respostas 5xx. A confiança em X-Forwarded-For só deve ser ativada quando o
app estiver atrás de proxy controlado que sobrescreva esse cabeçalho.

Arquivos enviados não passam por antivírus nesta release. Em uma implantação
aberta a terceiros, integre varredura antimalware e quarentena antes de liberar
downloads.
