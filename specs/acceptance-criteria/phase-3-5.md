# Phase 3.5 Acceptance Criteria

**AC35-001** Every accepted workflow carries a normalized data profile, processing context, and versioned policy decision.

**AC35-002** Policy evaluation occurs before workflow persistence and again before agent planning.

**AC35-003** In `enforce` mode, raw credentials and payment-card data are rejected before storage.

**AC35-004** Restricted data cannot be routed to an unapproved provider and receives explicit obligations when processed locally.

**AC35-005** `observe` and `warn` modes preserve a denial decision while allowing controlled legacy migration.

**AC35-006** Only the reviewed common baseline is active; industry overlays fail closed until legal and compliance review enables them.

**AC35-007** Policy outcomes are deterministic, auditable, visible through the API and web console, and covered by automated tests.

**AC35-008** No external provider, cloud service, regulated production data, or legal compliance claim is introduced.
