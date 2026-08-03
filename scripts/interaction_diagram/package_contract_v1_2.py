"""Interaction-contract declarations for compiler packages using v1.2.0."""
import hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; SCHEMA_ID='axiomiq_interactive_instructional_diagram_interaction_v1'; SCHEMA_VERSION='1.2.0'
PATHS={'interaction_schema_sha256':ROOT/'schemas/axiomiq_interactive_instructional_diagram_interaction_v1_2.schema.json','interaction_formula_registry_sha256':ROOT/'schemas/interaction_formula_registry_v1_2.json','interaction_renderer_registry_sha256':ROOT/'schemas/interaction_renderer_registry_v1_2.json','interaction_constraint_model_registry_sha256':ROOT/'schemas/interaction_constraint_model_registry_v1_2.json','interaction_display_vocabulary_registry_sha256':ROOT/'schemas/interaction_display_vocabulary_registry_v1_2.json'}
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def package_declaration(): return {'interaction_schema_id':SCHEMA_ID,'interaction_schema_version':SCHEMA_VERSION,**{k:digest(v) for k,v in PATHS.items()}}
def validate_package_declaration(package):
 expected=package_declaration(); return [f'{k} mismatch' for k,v in expected.items() if package.get(k)!=v]
