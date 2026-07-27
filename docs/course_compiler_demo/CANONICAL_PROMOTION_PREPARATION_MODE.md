# Canonical Promotion Preparation Mode

`CANONICAL_PROMOTION_PREPARATION` is a compiler-side, non-live mode for preparing reviewed compiler outputs for later human canonical review.

The mode normalizes document-driven compiler outputs and locked Phase E production outputs into a shared `PromotionPreparationInput` record. The downstream preparation pipeline consumes only that universal candidate contract, not dashboard mode names.

The mode writes only to an external preparation root. It rejects compiler-repository roots, adaptive-platform roots, Phase E family workspaces, relative roots, and symlink escapes.

Every preparation packet is explicitly noncanonical:

- `noncanonical=true`
- `human_review_required=true`
- `student_visible=false`
- `eligible_for_alpha_import=false`
- `canonical_promotion_authorized=false`
- `database_write_authorized=false`

Preparation packets may include qualification reports, fingerprint reports, duplicate reports, rights/provenance gap reports, asset reports, review checklists, blocked packets, prepared packets, and dry-run promotion manifests. They never assign authoritative canonical IDs, create canonical paths, write canonical repository records, produce SQL execution instructions, or contact a database.

The ten-record pilot intentionally exercises successful preparation and blocker paths: prepared review packets, rights/provenance escalation, asset/governance escalation, duplicate structural review, return for correction, and upstream regeneration. Synthetic document fixtures are labeled `SYNTHETIC_PROMOTION_PREPARATION_FIXTURE` when real reviewed document candidates are not available.
