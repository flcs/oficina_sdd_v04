# Quickstart: Pagina de Login com Admin Inicial

## Objetivo

Validar a feature de autenticacao e bootstrap administrativo seguindo
Test-Driven Development e a arquitetura planejada.

## Pre-requisitos

- Python 3.12 disponivel no ambiente.
- PostgreSQL disponivel com um banco dedicado para desenvolvimento e testes.
- Node.js 22+ e npm disponiveis para o frontend ReactJS + TypeScript.
- Variaveis de ambiente configuradas para conexao, chave JWT, emissor e
  audiencia do token.

## Fluxo recomendado de execucao

1. Criar o schema SQL inicial com tabela de contas, constraints de unicidade por
   email normalizado e colunas para bloqueio, troca obrigatoria de senha e
   versao de token.
2. Escrever os testes unitarios do dominio e dos casos de uso antes de qualquer
   implementacao.
3. Escrever os testes de contrato HTTP para login, consulta da identidade atual
   e troca da senha inicial, incluindo casos 400, 401 e 503 com
   `Retry-After`.
4. Escrever os testes de integracao com PostgreSQL real para SQL de repository,
   lockout, bootstrap idempotente e reativacao da conta administrativa.
5. Implementar o dominio, as portas e os adaptadores minimos para deixar a suite
   verde.
6. Refatorar mantendo todos os testes verdes e o strict typing em conformidade.
7. Implementar a camada frontend em ReactJS + TypeScript e validar integracao
   com os endpoints de autenticacao.
8. Coletar metricas da jornada de login e validar os criterios SC-001
   (jornada) e metas de latencia de API em ambiente de validacao.

## Cenarios de verificacao manual

1. Inicializar o ambiente sem usuarios e confirmar que existe exatamente uma
   conta `admin@empresa.com` com troca obrigatoria de senha.
2. Realizar login com as credenciais iniciais e confirmar recebimento de JWT no
   cabecalho bearer para chamadas subsequentes.
3. Tentar acessar um endpoint protegido antes da troca de senha e confirmar que
   apenas o fluxo minimo permitido e liberado.
4. Trocar a senha inicial, obter nova sessao valida e confirmar acesso pleno.
5. Executar cinco falhas consecutivas de login e confirmar bloqueio por 15
   minutos.
6. Aguardar a expiracao do bloqueio ou concluir um login posterior com sucesso e
   confirmar reinicio da contagem de falhas.
7. Simular indisponibilidade temporaria do servico de autenticacao e confirmar
   resposta 503 com header `Retry-After` e mensagem neutra.

## Suites esperadas

- `pytest tests/unit`
- `pytest tests/contract`
- `pytest tests/integration`
- `pytest tests/integration/performance`
- `npm run test -- --run` (frontend)

## Comandos de referencia

- `cd backend && pytest`
- `cd frontend && npm install`
- `cd frontend && npm run dev`
- `cd frontend && npm run test -- --run`

## Criterio de pronto para planejamento posterior

- Todos os testes da feature definidos antes da implementacao.
- Todos os contratos HTTP documentados e coerentes com a spec.
- Nenhuma dependencia concreta vazando para o dominio ou para os casos de uso.