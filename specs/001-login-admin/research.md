# Research: Pagina de Login com Admin Inicial

## Runtime e Dependencias

### Decision
Adotar Python 3.12 como runtime principal, FastAPI + Uvicorn para a interface
HTTP, psycopg 3 com psycopg_pool para acesso nativo ao PostgreSQL, PyJWT para
tokens, argon2-cffi para hashing de senha e Pydantic v2 com
pydantic-settings para validacao e configuracao.

### Rationale
Python 3.12 oferece melhor suporte a strict typing e simplifica o trabalho com
abstracoes fortemente tipadas. FastAPI reduz friccao para contratos HTTP e
testes de integracao. psycopg 3 atende a exigencia de driver nativo sem ORM,
mantendo SQL explicito e controle transacional. PyJWT e argon2-cffi cobrem os
requisitos centrais de seguranca sem empurrar complexidade de plataforma nesta
primeira entrega.

### Alternatives considered
- Django/Flask: rejeitados por adicionar convencoes extras ou menos suporte
  nativo a contratos tipados do que o necessario para esta entrega.
- SQLAlchemy ORM: rejeitado por conflitar com a exigencia de nao usar ORM.
- Async-first stack: rejeitada por aumentar complexidade sem ganho claro para um
  fluxo pequeno de autenticacao.

## Persistencia PostgreSQL Nativa

### Decision
Usar PostgreSQL com SQL explicito, queries parametrizadas do psycopg,
transacoes delimitadas por caso de uso de escrita e indice unico para email em
comparacao case-insensitive. Operacoes concorrentes de login e bootstrap devem
usar transacoes atomicas; login com atualizacao de falhas deve empregar
`SELECT ... FOR UPDATE`, e bootstrap deve usar `INSERT ... ON CONFLICT` ou
fluxo idempotente equivalente.

### Rationale
O recurso exige idempotencia para o administrador inicial, atualizacao segura do
contador de falhas e bloqueio temporario sem inconsistencias sob concorrencia.
Essas regras ficam mais previsiveis com SQL explicito e controle transacional no
limite do caso de uso.

### Alternatives considered
- Query builders pesados: rejeitados por reduzirem a transparencia do SQL sem
  necessidade real.
- Transacoes longas por request: rejeitadas por aumentarem risco de `idle in
  transaction` e acoplarem leituras simples a custos desnecessarios.

## Repository e Arquitetura Hexagonal

### Decision
Estruturar o backend em camadas de dominio, aplicacao, portas e adaptadores.
Casos de uso centrais: autenticar usuario, provisionar administrador inicial,
trocar senha inicial e autenticar token bearer. As portas principais serao
`UserAccountRepository`, `PasswordHasher`, `TokenService`, `Clock`,
`AuditLogPort` e `UnitOfWork`. Regras de lockout, provisao inicial e troca de
senha obrigatoria pertencem ao dominio/aplicacao, nunca ao controller HTTP nem
ao repositorio.

### Rationale
Essa divisao atende a constituicao do projeto: objetos coesos, dependencia de
abstracoes, SOLID e testabilidade. O padrao Repository isola SQL e mapeamento de
dados sem contaminar o dominio com detalhes de persistencia.

### Alternatives considered
- Colocar regras de login no controller: rejeitado por violar Hexagonal
  Architecture e reduzir testabilidade.
- Repositorio generico CRUD: rejeitado por esconder regras importantes e piorar
  clareza sobre SQL e transacoes de autenticacao.

## JWT no Cabecalho

### Decision
Transportar JWT somente em `Authorization: Bearer <token>`, com token de acesso
curto de 15 a 30 minutos, validacao de `iss`, `aud`, `sub`, `exp`, `iat` e
`jti`, e claims privadas `role`, `must_change_password` e mecanismo de
invalidacao vinculado a versao de token ou alteracao de senha. Mesmo apos
validacao criptografica, o backend deve consultar um resumo atual da conta para
verificar `active`, `locked_until`, `must_change_password` e revogacao.

### Rationale
JWT curto reduz superficie de exposicao. O recheck do estado atual da conta e
necessario para fazer valer bloqueio temporario, desativacao de conta e troca de
senha obrigatoria sem depender de expiracao natural do token.

### Alternatives considered
- Token em query string: rejeitado por risco de vazamento em logs e historico.
- Confiar apenas no JWT sem consulta de estado: rejeitado por dificultar
  revogacao imediata e enforcement de `must_change_password`.
- Refresh token nesta primeira entrega: rejeitado por ampliar a superficie de
  seguranca sem necessidade imediata.

## Estrategia de TDD

### Decision
Guiar a implementacao no ciclo red-green-refactor, com ordem fixa: testes
unitarios do dominio e aplicacao, testes de contrato HTTP, testes de integracao
com PostgreSQL real, implementacao minima e refatoracao. A suite inicial deve
cobrir login bem-sucedido, falha generica, bloqueio apos 5 falhas, reset da
contagem apos sucesso ou expiracao do bloqueio, bootstrap idempotente do admin,
reativacao de conta inconsistente e troca obrigatoria de senha no primeiro login.

### Rationale
Essa estrategia maximiza seguranca contra regressao em regras de autenticacao e
mantem o desenho orientado por comportamento observavel, coerente com a
constituicao do repositorio.

### Alternatives considered
- Priorizar testes de integracao antes de unitarios: rejeitado por alongar o
  ciclo de feedback e dificultar evolucao do dominio.
- Mockar driver nativo em testes de persistencia: rejeitado por nao validar SQL,
  constraints e concorrencia reais.

## Riscos e Tradeoffs

### Decision
Aceitar explicitamente os riscos controlados da senha bootstrap `admin` e do
bloqueio por conta, mitigando-os com `must_change_password=true`, logging do
bootstrap, mensagem generica de falha e recuperacao de estado via consulta ao
banco em requests autenticados.

### Rationale
Esses riscos derivam da propria especificacao, entao a melhor resposta de design
e cercar a implementacao com controles objetivos e testaveis, sem expandir o
escopo desnecessariamente.

### Alternatives considered
- Remover senha padrao: rejeitado por conflitar com a especificacao.
- Bloqueio por origem em vez de por conta: rejeitado porque a clarificacao da
  spec fixou bloqueio temporario por conta.