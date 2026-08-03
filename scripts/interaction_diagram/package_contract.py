"""Interaction-contract declarations required on compiler packages."""
from __future__ import annotations
import hashlib
from pathlib import Path
SCHEMA_ID='axiomiq_interactive_instructional_diagram_interaction_v1'
SCHEMA_VERSION='1.1.0'
SCHEMA_PATH=Path(__file__).resolve().parents[2]/'schemas'/'axiomiq_interactive_instructional_diagram_interaction_v1_1.schema.json'
FORMULA_REGISTRY_PATH=SCHEMA_PATH.with_name('interaction_formula_registry_v1_1.json')
RENDERER_REGISTRY_PATH=SCHEMA_PATH.with_name('interaction_renderer_registry_v1_1.json')
def schema_sha256(): return hashlib.sha256(SCHEMA_PATH.read_bytes()).hexdigest()
def _digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def package_declaration(): return {'interaction_schema_id':SCHEMA_ID,'interaction_schema_version':SCHEMA_VERSION,'interaction_schema_sha256':schema_sha256(),'interaction_formula_registry_sha256':_digest(FORMULA_REGISTRY_PATH),'interaction_renderer_registry_sha256':_digest(RENDERER_REGISTRY_PATH)}
def validate_package_declaration(package):
    expected=package_declaration(); return [f'{k} mismatch' for k,v in expected.items() if package.get(k)!=v]
