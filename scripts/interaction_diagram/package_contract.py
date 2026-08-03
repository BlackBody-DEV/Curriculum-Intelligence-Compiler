"""Interaction-contract declarations required on compiler packages."""
from __future__ import annotations
import hashlib
from pathlib import Path
SCHEMA_ID='axiomiq_interactive_instructional_diagram_interaction_v1'
SCHEMA_VERSION='1.1.0'
SCHEMA_PATH=Path(__file__).resolve().parents[2]/'schemas'/'axiomiq_interactive_instructional_diagram_interaction_v1_1.schema.json'
def schema_sha256(): return hashlib.sha256(SCHEMA_PATH.read_bytes()).hexdigest()
def package_declaration(): return {'interaction_schema_id':SCHEMA_ID,'interaction_schema_version':SCHEMA_VERSION,'interaction_schema_sha256':schema_sha256()}
def validate_package_declaration(package):
    expected=package_declaration(); return [f'{k} mismatch' for k,v in expected.items() if package.get(k)!=v]
