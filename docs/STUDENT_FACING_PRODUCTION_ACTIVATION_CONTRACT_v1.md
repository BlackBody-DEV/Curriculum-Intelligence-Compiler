# Student-Facing Production Activation Contract v1

This contract closes the standalone compiler's nonprotected side of the production boundary. It defines a deterministic proposed import package, capability negotiation, authenticated ownership, idempotency, retry, rollback, deployment prerequisites, and a synthetic end-to-end rehearsal. It performs no live operation.

The import unit is one validated question revision, its complete lineage, and its assessment links. A stable idempotency key covers source identity, source revision, and content checksum. Replaying that key is a no-op; the same identity and revision with different content is a permanent conflict. Validation, identity, lineage, checksum, topic, and capability failures never retry. Only named transient infrastructure failures retry, with a bounded schedule.

All imported questions start inactive, not serving-eligible, and not student-visible. Import and activation are separate transactions and roles. The import actor must hold `curriculum_importer`; the activation actor must hold `curriculum_publisher`. Student identity always comes from the verified authentication mapping, never a client-supplied user identifier. An unsupported answer capability rejects before import, and silent fallback is forbidden.

The protected execution must preserve immutable import and activation journals. Pre-activation rollback rejects the batch and removes only inactive links. Post-activation rollback first disables serving and activity, restores the prior serving revision, and retains all student attempts and audit history.

Production deployment is blocked until the exact adaptive commit, migrations, database reachability, canonical approval, adaptive write approval, student-visibility approval, answer-capability parity, ownership tests, disabled initial feature flag, and rollback rehearsal are all independently verified.
