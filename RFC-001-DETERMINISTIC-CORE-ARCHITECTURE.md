# RFC-001-DETERMINISTIC-CORE-ARCHITECTURE

## Purpose

Define the official conceptual architecture, ownership boundaries, operational constraints, deterministic doctrine, lifecycle responsibilities, and system contracts governing the Trady AI Deterministic Core.

This RFC establishes the foundational execution architecture of the system.

This document defines:

* conceptual ownership
* execution boundaries
* deterministic guarantees
* operational constraints
* lifecycle responsibilities
* architectural invariants
* forbidden behaviors
* system interaction contracts

This RFC does NOT define:

* implementation details
* folder structure
* exact algorithms
* database schemas
* deployment configuration
* runtime infrastructure specifics

Those belong to SDD-level documents.

---

# Core Principle

```text
The Deterministic Core executes.
It does not improvise.
```

The deterministic core is the operational execution authority of Trady AI.

It exists to:

* process deterministic financial workflows
* execute bounded strategies
* preserve reproducibility
* maintain statistical traceability
* expose auditable operational behavior

The deterministic core must remain operationally stable independent of intelligence layers.

---

# Architectural Identity

The Deterministic Core is:

* platform-agnostic
* model-agnostic
* deterministic-first
* execution-oriented
* operationally thin
* audit-oriented
* reproducibility-preserving

The Deterministic Core is NOT:

* an orchestration framework
* an intelligence system
* an adaptive runtime
* an autonomous governance layer
* a semantic reinterpretation layer
* a probabilistic execution engine

---

# Primary Responsibilities

The Deterministic Core owns:

* deterministic execution sequencing
* signal lifecycle management
* market state processing
* statistical computation
* strategy execution coordination
* risk enforcement
* position lifecycle tracking
* deterministic replayability
* operational observability
* execution logging

The Deterministic Core does NOT own:

* intelligence reasoning
* architectural governance
* semantic reinterpretation
* strategy invention
* autonomous adaptation
* platform-specific semantics
* UI logic
* presentation logic

---

# Deterministic Doctrine

The Deterministic Core must preserve:

* explicit execution
* reproducible outputs
* traceable state transitions
* bounded lifecycle behavior
* observable failures
* explicit contracts
* fail-fast behavior

The following are prohibited:

* hidden retries
* implicit recovery
* silent correction
* probabilistic execution paths
* runtime mutation
* hidden orchestration
* semantic enrichment
* uncontrolled async behavior

Identical inputs must produce structurally identical outputs.

---

# Operational Boundaries

The Deterministic Core may:

* consume normalized platform data
* process deterministic strategies
* evaluate bounded conditions
* enforce risk rules
* execute approved operations
* expose structured observability

The Deterministic Core must NOT:

* modify governance authority
* rewrite contracts
* infer semantic meaning
* mutate frozen boundaries
* bypass adapter contracts
* own platform integrations
* introduce orchestration layers

---

# Relationship With Intelligence Systems

Intelligence systems are external analytical layers.

Examples:

* Hermes
* Pythy
* GPT
* Claude
* future analytical systems

The Deterministic Core exposes observability to intelligence layers.

The Deterministic Core does NOT depend operationally on intelligence layers.

If all intelligence systems are removed:
the deterministic core must remain fully functional.

---

# Relationship With Platform Adapters

Platform adapters isolate external systems from the deterministic core.

Adapters:

* normalize external structures
* expose frozen contracts
* preserve deterministic equivalence

The deterministic core consumes only frozen internal contracts.

The deterministic core must never directly depend on:

* exchange-specific semantics
* broker-specific assumptions
* external API structures

---

# Risk Philosophy

The Deterministic Core is treated as high-risk infrastructure because it may control financial execution.

Therefore:

* bounded execution is mandatory
* explicit observability is mandatory
* rollback capability is mandatory
* deterministic replayability is mandatory
* operational traceability is mandatory

Correctness has higher priority than execution speed.

---

# Lifecycle Responsibilities

The Deterministic Core lifecycle sequence is:

```text
Input
→ Validation
→ Normalization
→ State Processing
→ Signal Evaluation
→ Risk Enforcement
→ Execution Decision
→ Logging
→ Observability Output
```

No lifecycle stage may absorb ownership from another stage.

---

# Architectural Constraints

The Deterministic Core must remain:

* operationally minimal
* understandable
* auditable
* replaceable
* evolvable
* bounded
* dependency-light

The architecture rejects:

* orchestration inflation
* framework-driven evolution
* hidden state systems
* recursive execution systems
* distributed runtime expansion
* speculative scalability

---

# Failure Philosophy

Failures must remain:

* explicit
* attributable
* reproducible
* observable

The system rejects:

* silent degradation
* hidden fallback logic
* invisible retries
* automatic semantic repair

Fail-fast behavior is mandatory.

---

# Official Phase Relationship

This RFC governs:

```text
MASTER ROADMAP
→ FASE 1 — DETERMINISTIC CORE
```

Future SDDs implementing this RFC must preserve:

* deterministic-first philosophy
* bounded execution doctrine
* thin runtime doctrine
* explicit ownership boundaries
* platform isolation
* intelligence isolation

---

# Final Principle

```text
Deterministic execution is infrastructure.
Not intelligence.
```

The deterministic core succeeds only if:

* operational behavior remains predictable
* architecture remains bounded
* execution remains reproducible
* intelligence remains externalized
* governance remains authoritative
