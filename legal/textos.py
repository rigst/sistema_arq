"""Texto da versão 1.0 dos documentos legais.

Fica em módulo próprio para a migração de dados poder importá-lo e para
facilitar redigir a próxima versão ao lado da anterior. Publicar uma versão
nova é criar outro DocumentoLegal com `versao` diferente e `vigente_desde`
preenchido — o middleware volta a exigir aceite de todo mundo.
"""

TERMOS_V1 = """\
Estes termos valem entre você e quem opera o A.R.Q. Ao criar uma conta, entrar \
como visitante ou usar o sistema, você concorda com o que está escrito aqui.

## O que é o A.R.Q.

O A.R.Q. é um sistema de gestão para escritórios de arquitetura e design de \
interiores. Ele reúne clientes, propostas, contratos, projetos, obras, tarefas, \
agenda, precificação, financeiro e obrigações técnicas em um só lugar.

O sistema está em desenvolvimento, com foco em aprendizado e portfólio. Funções \
podem mudar, e podem existir falhas.

## Sua conta

Você é responsável por manter sua senha em segredo e por tudo que acontece na sua \
conta. Avise assim que suspeitar de acesso indevido.

Cada escritório enxerga apenas os próprios dados. Não tente acessar dados de outro \
escritório, burlar limites do sistema ou automatizar acessos em volume.

## Acesso visitante

O acesso visitante cria um escritório temporário para você conhecer a interface. \
Ele é descartável:

- os dados são de demonstração e não devem ser usados para trabalho real;
- o escritório temporário e tudo que ele contém são apagados automaticamente \
depois de 24 horas;
- não há como recuperar nada depois disso.

## Os dados que você cadastra

Os dados que você lança no sistema continuam seus. Você é quem responde pelo \
conteúdo — inclusive por ter base legal para tratar dados de clientes e de \
terceiros que cadastrar aqui.

Nós tratamos esses dados para operar o sistema. Os detalhes estão na Política de \
Privacidade.

## O que não prometemos

O sistema é oferecido no estado em que se encontra. Não garantimos que estará \
sempre disponível, livre de erros ou adequado a um fim específico.

Os cálculos de hora técnica, margem, cronograma e resultado são apoio à decisão, \
não aconselhamento contábil, jurídico ou de engenharia. Confira antes de usar em \
proposta, contrato ou obra.

O controle de ART, RRT e vínculo CAU serve para lembrar prazos. A obrigação de \
registrar e manter em dia continua sendo sua e do responsável técnico.

## Encerramento

Você pode parar de usar quando quiser e pedir a exclusão da conta. Podemos suspender \
um acesso que viole estes termos ou coloque o sistema em risco.

## Mudanças nestes termos

Quando estes termos mudarem, publicamos uma versão nova e pedimos seu aceite antes \
de continuar usando. As versões aceitas ficam registradas com data e hora.

## Lei aplicável

Vale a lei brasileira, e fica eleito o foro da comarca de domicílio do usuário para \
resolver o que não for resolvido de forma amigável.
"""

PRIVACIDADE_V1 = """\
Esta política explica quais dados pessoais o A.R.Q. trata, por quê, por quanto tempo \
e o que você pode pedir. Ela segue a Lei Geral de Proteção de Dados (Lei 13.709/2018).

## Quem trata os dados

Quem opera esta instalação do A.R.Q. é o controlador dos dados de conta e de uso. \
Em relação aos dados que você cadastra sobre seus clientes e projetos, você é o \
controlador e nós agimos como operador, seguindo suas instruções.

## Dados que tratamos

Dados de conta: usuário, nome de exibição, perfil, escritório e data de criação.

Dados de uso: data e hora de acesso, endereço IP e identificação do navegador, \
registrados nos aceites de termos e nos registros técnicos do servidor.

Dados que você cadastra: clientes, contatos, propostas, contratos, projetos, obras, \
visitas, tarefas, lançamentos financeiros e obrigações técnicas. Aqui pode haver \
dados pessoais de terceiros que você inseriu.

Não pedimos e não queremos dados sensíveis nem dados de crianças e adolescentes.

## Por que tratamos

- Executar o contrato de uso do sistema e manter sua conta funcionando.
- Cumprir obrigação legal e comprovar o aceite dos termos, que é o motivo de \
guardarmos data, hora, IP e navegador de cada aceite.
- Interesse legítimo em manter o sistema seguro, prevenir abuso e corrigir falhas.

Não vendemos dados pessoais e não usamos seus dados para publicidade.

## Cookies

Usamos apenas cookies necessários: o de sessão, que mantém você conectado, e o de \
proteção contra falsificação de requisição (CSRF). Não usamos cookies de análise \
nem de terceiros.

## Com quem compartilhamos

Com a infraestrutura que hospeda o sistema, no limite necessário para ele funcionar. \
Com autoridades, quando houver obrigação legal. Fora isso, não compartilhamos.

## Por quanto tempo guardamos

Dados de conta e de negócio: enquanto a conta existir, e por até 5 anos depois do \
encerramento quando houver necessidade de defesa em processo.

Escritório visitante: apagado automaticamente 24 horas depois da criação, junto com \
tudo que foi cadastrado nele.

Registros de aceite: mantidos enquanto forem necessários como prova do consentimento \
ao contrato.

## Seus direitos

Você pode pedir a qualquer momento: confirmação de que tratamos seus dados, acesso, \
correção, anonimização, portabilidade, informação sobre compartilhamentos e exclusão \
do que não precisamos manter por obrigação legal.

Para exercer qualquer um deles, fale com quem opera esta instalação do sistema. \
Respondemos em até 15 dias.

## Segurança

Usamos conexão criptografada, senhas guardadas com hash, separação de dados por \
escritório e cabeçalhos de segurança no navegador. Nenhum sistema é infalível — se \
houver incidente relevante, comunicamos os afetados e a ANPD.

## Mudanças nesta política

Quando esta política mudar, publicamos uma versão nova e pedimos seu aceite antes de \
continuar usando. As versões aceitas ficam registradas com data e hora.
"""


# --- v1.1: acrescenta licença do software, autoria e contato ---------------

_LICENCA_E_CONTATO = """\
## Licença do software

O A.R.Q. é software proprietário. O código-fonte e os arquivos que o acompanham \
pertencem ao autor, e o copyright está registrado no arquivo LICENSE do projeto.

Ao usar o sistema você recebe uma licença de uso pessoal, limitada, revogável e \
intransferível — nada além disso. Não é concedida permissão para copiar, modificar, \
distribuir, sublicenciar, vender ou fazer engenharia reversa do software sem \
autorização prévia e por escrito do autor.

O software é fornecido no estado em que se encontra, sem garantia de qualquer tipo, \
como já diz a seção "O que não prometemos".

A licença trata do software. Ela não alcança:

- os dados que você cadastra, que continuam seus;
- as bibliotecas de terceiros, cada uma sob a própria licença (ver LICENCAS.md);
- as fotografias da interface, sob a Unsplash License;
- as fontes Archivo e IBM Plex, sob a SIL Open Font License 1.1.

A marca A.R.Q. e o nome Stölben não são licenciados para uso de terceiros.

## Quem responde por este sistema

O A.R.Q. é desenvolvido e operado por:

**Rodrigo Stölben** — desenvolvedor de software

- Site: stolben.com
- E-mail: rodrigo@stolben.com
- Código: github.com/rigst

Esse é o canal para dúvidas sobre estes termos, pedidos relacionados aos seus dados \
pessoais (previstos na Política de Privacidade) e qualquer relato de problema ou \
falha de segurança.
"""

TERMOS_V11 = TERMOS_V1.replace(
    "## Lei aplicável", _LICENCA_E_CONTATO + "\n## Lei aplicável"
)

PRIVACIDADE_V11 = PRIVACIDADE_V1.replace(
    "## Quem trata os dados\n\nQuem opera esta instalação do A.R.Q. é o controlador",
    "## Quem trata os dados\n\n**Rodrigo Stölben** (stolben.com · rodrigo@stolben.com), "
    "que opera esta instalação do A.R.Q., é o controlador",
).replace(
    "Para exercer qualquer um deles, fale com quem opera esta instalação do sistema. \\\nRespondemos em até 15 dias.",
    "Para exercer qualquer um deles, escreva para rodrigo@stolben.com. Respondemos em \\\naté 15 dias.",
)
