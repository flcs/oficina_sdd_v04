<!--
Relatorio de Impacto de Sincronizacao
Version change: template -> 1.0.0
Principios modificados:
- Template Principle 1 -> I. Object-Oriented Design First
- Template Principle 2 -> II. Depend on Abstractions
- Template Principle 3 -> III. SOLID with Strict Typing
- Template Principle 4 -> IV. Test-Driven Development Mandatory
- Template Principle 5 -> V. Clarity and Maintainability Over Cleverness
Secoes adicionadas:
- Engineering Constraints
- Delivery Workflow and Quality Gates
Secoes removidas:
- None
Templates que exigiram atualizacao:
- ✅ updated .specify/templates/plan-template.md
- ✅ updated .specify/templates/spec-template.md
- ✅ updated .specify/templates/tasks-template.md
- ✅ no command templates present under .specify/templates/commands/
- ✅ no runtime guidance documents requiring synchronization were found
TODOs de acompanhamento:
- None
-->

# Oficina SDD Constitution

## Principios Centrais

### I. Object-Oriented Design First
Todo codigo de producao DEVE ser modelado por meio de objetos explicitos com
responsabilidades claras, contratos públicos estáveis e comportamento coeso. As
features MUST ser decompostas em entidades de dominio, value objects, services e
componentes de orquestracao, em vez de scripts procedurais ou fluxos utilitarios
ad hoc. Object composition e o mecanismo padrao para reuso de comportamento;
inheritance e permitida apenas quando preserva substitutability e reduz
duplicacao sem esconder o control flow. Rationale: um modelo de objetos
consistente melhora a rastreabilidade, isola mudancas e mantem o sistema
compreensivel a medida que cresce.

### II. Depend on Abstractions
Politicas de alto nivel MUST depender de interfaces, protocols ou abstract base
classes em vez de implementacoes concretas. Preocupacoes de infrastructure como
I/O, persistence, external services, clocks e randomness MUST entrar no sistema
por meio de abstractions injetaveis para que possam ser substituidas em testes e
evoluidas sem reescrever a domain logic. A construcao direta de concrete
dependencies dentro de business rules e proibida, a menos que o proprio
componente seja o composition root. Rationale: dependency inversion reduz o
acoplamento e mantem o codebase aberto a mudancas sem desestabilizar o
comportamento central.

### III. SOLID with Strict Typing
Toda mudanca MUST satisfazer os principios SOLID e MUST preservar strict Python
typing em codigo de producao e de teste. Single Responsibility, Open/Closed,
Liskov Substitution, Interface Segregation e Dependency Inversion sao criterios
de review, nao orientacoes opcionais. Public APIs, colaboradores internos,
fixtures e data structures MUST declarar tipos precisos; o uso de untyped defs,
implicit Any ou contratos amplos em formato de objeto e proibido, salvo quando
um boundary explicito e documentado tornar isso inevitavel. Rationale: strict
types e SOLID design criam contratos verificaveis mecanicamente e evitam
architecture drift.

### IV. Test-Driven Development Mandatory
TDD e inegociavel para toda mudanca de comportamento. O trabalho MUST seguir o
red-green-refactor cycle: definir o comportamento esperado, escrever um
automated test que falhe pelo motivo pretendido, implementar a menor mudanca que
faca o teste passar e depois refatorar mantendo a suite green. Unit tests sao a
evidencia padrao para a domain logic; integration e contract tests MUST cobrir
comportamento entre boundaries, dependency wiring e regressions em contratos
compartilhados. Nenhuma implementacao de producao pode ser merged sem evidencia
previa de failing test ou sem uma excecao explicita por escrito aprovada durante
o review. Rationale: TDD mantem requirements executaveis e protege a
maintainability diante de mudancas.

### V. Clarity and Maintainability Over Cleverness
Implementacoes MUST priorizar nomes legiveis, metodos pequenos, invariants
explicitas e control flow direto em vez de abstractions excessivamente concisas
ou generalizacao especulativa. Cada modulo MUST ter um unico proposito obvio,
cada classe MUST expor comportamento por meio de metodos que revelem a intencao
e cada mudanca MUST reduzir ou conter o cognitive load. Optimizacoes,
framework indirection e advanced language features exigem uma necessidade
mensuravel e uma analise de alternativa mais simples. Rationale: este projeto
otimiza para operabilidade de longo prazo, nao para novidade de curto prazo.

## Restricoes de Engenharia

- Python code MUST executar com strict static type checking habilitado e MUST
  nao introduzir novas supressoes de type-checking sem justificativa
  documentada.
- Architectural boundaries MUST ser explicitas em plans, specs e tasks,
  incluindo quais abstractions isolam a domain logic da infrastructure.
- Novas features MUST definir o escopo de unit tests e toda coverage de
  integration ou contract tests antes do inicio da implementacao.
- Shared utilities MUST surgir apenas depois que a duplicacao for observada em
  pelo menos dois use cases concretos; frameworks prematuros e god objects sao
  proibidos.
- Reviews MUST rejeitar mudancas que contornem abstractions, colapsem object
  responsibilities ou troquem maintainability por conveniencia local.

## Workflow de Entrega e Quality Gates

Todo implementation plan MUST incluir um constitution check que verifique
object boundaries, abstraction-driven dependencies, impacto em SOLID, strict
typing e estrategia de TDD. Toda feature specification MUST registrar user
scenarios testaveis de forma independente, alem de restricoes explicitas de
arquitetura e qualidade. Toda task list MUST ordenar testes antes da
implementacao e incluir trabalho de typing, design boundaries e refactoring
quando necessario. Antes de merge, reviewers MUST confirmar que os testes foram
escritos primeiro, que a automated suite passa e que nenhum atalho arquitetural
novo ou regressao de typing foi introduzido.

## Governanca

Esta constitution se sobrepoe a praticas locais conflitantes do repositorio.
Amendments exigem: (1) uma proposta por escrito descrevendo a mudanca de
governanca, (2) sincronizacao dos templates e workflow documents afetados e (3)
aprovacao explicita em review pelos mantenedores do projeto. O versioning segue
regras semanticas para documentos de governanca: MAJOR para mudancas ou remocoes
de principios incompatíveis, MINOR para novos principios ou obrigacoes
materialmente expandidas e PATCH para esclarecimentos que nao alterem o
comportamento de compliance. Compliance review e obrigatorio para todo plan,
spec, task list e code review; violacoes MUST ser documentadas no artifact
relevante com uma decisao de remediacao delimitada no tempo.

**Version**: 1.0.0 | **Ratified**: 2026-03-13 | **Last Amended**: 2026-03-13
