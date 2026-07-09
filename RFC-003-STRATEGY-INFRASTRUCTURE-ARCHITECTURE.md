# RFC-003-STRATEGY-INFRASTRUCTURE-ARCHITECTURE

## Purpose

Define the official conceptual architecture, ownership boundaries, operational doctrine, lifecycle responsibilities, and isolation principles governing deterministic strategy systems inside Trady AI.

This RFC establishes the official architecture for:

* strategy definition
* signal generation
* statistical decision systems
* strategy lifecycle separation
* deterministic analytical execution
* bounded financial decision logic

This document defines:

* strategy doctrine
* signal philosophy
* strategy ownership boundaries
* deterministic strategy constraints
* strategy lifecycle behavior
* isolation doctrine
* statistical traceability requirements
* forbidden strategy behaviors

This RFC does NOT define:

* specific algorithms
* mathematical implementations
* indicator formulas
* statistical models
* strategy parameters
* database schemas
* implementation details

Those belong to SDD-level documents.

---

# Core Principle

```text id="0e5z2r"
Strategies generate signals.
They do not own execution authority.
```

Strategies are bounded analytical systems.

They evaluate deterministic conditions and expose structured decision outputs.

The deterministic core owns execution authority.

---

# Architectural Identity

Strategy systems are:

* deterministic
* modular
* isolated
* auditable
* replaceable
* statistically traceable
* execution-independent

Strategy systems are NOT:

* orchestration engines
* autonomous agents
* governance systems
* execution authorities
* intelligence runtimes
* platform integrations
* semantic reinterpretation systems

---

# Official Strategy Doctrine

A strategy is a bounded deterministic analytical module responsible for:

* processing normalized market states
* evaluating explicit conditions
* calculating bounded statistical outputs
* generating structured signals
* exposing reproducible decision logic

Strategies must remain:

* deterministic
* testable
* replayable
* isolated
* observable
* statistically auditable

---

# Primary Responsibilities

Strategy systems own:

* signal generation
* state evaluation
* bounded statistical analysis
* deterministic calculations
* condition evaluation
* confidence estimation
* strategy-local reasoning
* analytical observability

Strategy systems do NOT own:

* trade execution
* platform interaction
* governance authority
* orchestration behavior
* runtime lifecycle coordination
* external API handling
* intelligence reflection
* portfolio governance

---

# Signal Philosophy

Signals are structured deterministic outputs.

Signals represent:

* analytical conclusions
* statistical evaluations
* bounded recommendations
* explicit strategy states

Signals are NOT:

* execution commands
* autonomous authority
* platform operations
* governance overrides

The deterministic core evaluates signals before execution decisions occur.

---

# Deterministic Strategy Doctrine

Strategies must preserve:

* reproducible calculations
* explicit logic
* deterministic evaluation
* bounded state transitions
* traceable outputs
* explicit failure behavior

The following are prohibited:

* hidden adaptive behavior
* implicit learning
* probabilistic runtime mutation
* self-modifying logic
* opaque execution paths
* hidden state mutation
* invisible parameter drift

Identical inputs must produce structurally identical outputs.

---

# Strategy Isolation Doctrine

Strategies must remain operationally isolated.

A strategy may NOT:

* mutate unrelated strategies
* inherit uncontrolled context
* absorb adapter ownership
* reinterpret execution semantics
* mutate governance constraints
* contaminate unrelated execution domains

Every strategy must be independently:

* testable
* removable
* replaceable
* auditable
* replayable

Isolation is mandatory.

---

# Relationship With Deterministic Core

The deterministic core owns:

* execution authority
* risk enforcement
* lifecycle sequencing
* operational coordination

Strategies expose signals only.

Strategies never:

* place orders
* control execution timing
* mutate execution rules
* bypass risk systems
* own portfolio authority

Execution remains externalized.

---

# Relationship With Platform Adapters

Strategies consume only normalized internal contracts.

Strategies must never:

* directly call exchange APIs
* depend on SDK behavior
* consume platform-native payloads
* inherit platform semantics
* absorb integration ownership

Platform isolation remains mandatory.

---

# Relationship With Intelligence Systems

Intelligence systems may:

* analyze strategy performance
* evaluate signal quality
* detect drift
* propose adjustments
* summarize behavior

Intelligence systems must NOT:

* mutate strategy behavior dynamically
* bypass deterministic evaluation
* rewrite frozen strategy contracts
* inject hidden execution behavior

Strategy execution remains deterministic.

---

# Statistical Traceability Doctrine

Every strategy must preserve:

* signal lineage
* parameter lineage
* evaluation lineage
* execution correlation
* replay capability
* historical observability

Statistical outputs must remain:

* attributable
* reproducible
* auditable
* bounded

Opaque statistical behavior is prohibited.

---

# Initial Strategy Focus

Initial V1 strategy family:

```text id="mh0okx"
Markov Persistence Strategies
```

Examples:

* directional persistence
* volatility persistence
* continuation probabilities
* state-transition probabilities

The initial objective is:

* deterministic statistical validation
* reproducible execution
* bounded experimentation

NOT:

* maximizing profitability
* predictive hype systems
* autonomous speculative intelligence

---

# Future Strategy Families

Future isolated strategy modules may include:

* momentum systems
* mean reversion systems
* volatility compression systems
* cross-market divergence systems
* long-term allocation systems
* portfolio balancing systems
* statistical arbitrage systems

All future strategies must preserve:

* deterministic doctrine
* isolation doctrine
* auditability
* bounded operational behavior

---

# Execution Domain Relationship

Strategies belong to isolated execution domains.

Examples:

* PM-5M
* BINANCE-INTRADAY
* SWING-30D
* LONG-TERM-5Y

Strategies must not contaminate:

* unrelated domains
* unrelated risk systems
* unrelated statistical baselines

Cross-domain contamination is prohibited.

---

# Risk Philosophy

Strategies are treated as high-risk analytical systems because they influence financial execution.

Therefore:

* explicit observability is mandatory
* replayability is mandatory
* parameter traceability is mandatory
* bounded experimentation is mandatory
* statistical validation is mandatory

The system rejects:

* opaque predictive behavior
* hidden adaptive systems
* uncontrolled optimization loops
* invisible parameter mutation

Correctness has higher priority than complexity.

---

# Failure Philosophy

Strategy failures must remain:

* explicit
* attributable
* reproducible
* observable

The system rejects:

* silent degradation
* hidden fallback logic
* invisible recalibration
* implicit signal correction

Fail-fast behavior is mandatory.

---

# Architectural Constraints

Strategy systems must remain:

* operationally minimal
* understandable
* bounded
* deterministic
* modular
* dependency-light
* replaceable

The architecture rejects:

* strategy orchestration frameworks
* recursive strategy coordination
* autonomous strategy swarms
* hidden optimization systems
* speculative abstraction layering

Complexity must justify itself continuously.

---

# Official Phase Relationship

This RFC governs:

```text id="4t0rx8"
MASTER ROADMAP
→ FASE 3 — STRATEGY INFRASTRUCTURE
```

Future SDDs implementing this RFC must preserve:

* deterministic signal generation
* strategy isolation
* statistical traceability
* bounded execution philosophy
* platform isolation
* intelligence externalization

---

# Final Principle

```text id="jvzb5v"
Strategies evaluate conditions.
The deterministic core decides execution.
```

The strategy infrastructure succeeds only if:

* strategies remain isolated
* signals remain auditable
* execution remains externalized
* intelligence remains bounded
* statistical behavior remains reproducible
