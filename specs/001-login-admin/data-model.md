# Data Model: Pagina de Login com Admin Inicial

## Conta de Usuario

### Campos
- `account_id`: identificador unico da conta.
- `email`: endereco autenticavel unico, comparado sem diferenca entre maiusculas
  e minusculas.
- `password_hash`: hash Argon2id da senha vigente.
- `role`: papel de acesso da conta, incluindo perfil administrativo.
- `active`: indica se a conta pode autenticar.
- `must_change_password`: indica se a conta precisa trocar a senha antes de usar
  totalmente o sistema.
- `failed_login_attempts`: contador de falhas consecutivas.
- `locked_until`: instante ate o qual a conta fica bloqueada.
- `token_version`: versao para invalidação de tokens emitidos anteriormente.
- `created_at`: instante de criacao.
- `updated_at`: instante da ultima alteracao persistida.
- `last_login_at`: instante do ultimo login bem-sucedido, quando houver.

### Regras de Validacao
- `email` MUST ser obrigatorio, normalizado e unico.
- `password_hash` MUST existir para toda conta autenticavel.
- `failed_login_attempts` MUST ser zero ou positivo.
- `locked_until` MUST ser nulo quando a conta nao estiver bloqueada.
- `must_change_password` MUST iniciar como verdadeiro para a conta bootstrap.

### Transicoes de Estado
- `Provisioned`: conta criada ativa e com `must_change_password=true`.
- `Active`: conta ativa e apta a autenticar.
- `Locked`: conta ativa, mas temporariamente impedida de autenticar ate
  `locked_until`.
- `Inactive`: conta desativada para autenticacao.
- `Recovered`: conta administrativa bootstrap reativada e marcada para reset de
  senha.

## Sessao de Autenticacao

### Campos
- `account_id`: identidade autenticada.
- `access_token`: JWT emitido para acesso.
- `issued_at`: instante de emissao.
- `expires_at`: instante de expiracao.
- `must_change_password`: espelha a restricao da conta no contexto da sessao.

### Regras de Validacao
- `access_token` MUST conter `sub`, `iss`, `aud`, `exp`, `iat` e `jti`.
- `expires_at` MUST ser posterior a `issued_at`.

## Tentativa de Login

### Campos
- `attempt_id`: identificador unico do evento.
- `email_submitted`: email informado pelo usuario.
- `account_id`: conta afetada, quando resolvida com seguranca.
- `outcome`: sucesso, credencial invalida, bloqueio, indisponibilidade ou reset
  obrigatorio pendente.
- `occurred_at`: instante da tentativa.
- `source_ip`: origem da requisicao, quando disponivel.
- `user_agent`: identificacao do cliente, quando disponivel.

### Regras de Validacao
- `outcome` MUST pertencer ao conjunto controlado de resultados conhecidos.
- Eventos de falha MUST manter mensagem de apresentacao generica ao usuario.

## Provisionamento Inicial de Administrador

### Campos
- `target_email`: email administrativo padrao, fixado em `admin@empresa.com`.
- `action`: criado, preservado, reativado ou normalizado.
- `performed_at`: instante da execucao.
- `requires_password_reset`: indica obrigatoriedade de troca de senha apos a
  provisao.

### Regras de Validacao
- A provisao MUST ser idempotente.
- O processo MUST preservar exatamente uma conta administrativa bootstrap.

## Relacionamentos
- Uma `Conta de Usuario` pode originar varias `Tentativas de Login`.
- Uma `Conta de Usuario` pode originar varias `Sessoes de Autenticacao` ao longo
  do tempo.
- O `Provisionamento Inicial de Administrador` atua sobre exatamente uma
  `Conta de Usuario` bootstrap.