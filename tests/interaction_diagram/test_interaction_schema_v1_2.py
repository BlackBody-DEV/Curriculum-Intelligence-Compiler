import copy,hashlib,json
from pathlib import Path
import jsonschema,pytest
from scripts.interaction_diagram.formulas_v1_2 import FORMULA_METADATA,FormulaError,evaluate_formula,evaluate_reference_case
from scripts.interaction_diagram.package_contract_v1_2 import package_declaration,validate_package_declaration
from scripts.interaction_diagram.validate_interaction_spec_v1_2 import validate_interaction_spec
ROOT=Path(__file__).resolve().parents[2]
def load(p): return json.loads((ROOT/p).read_text())
V1='fixtures/interaction_diagrams/vectors_component_resolution_and_addition_explanation_v1.json'; V11='fixtures/interaction_diagrams/vectors_component_resolution_and_addition_explanation_v1_1.json'; V12='fixtures/interaction_diagrams/statics_fbd_3d_hydrostatic_reference_v1_2.json'

def test_v1_and_v11_canonical_bytes_are_immutable():
 expected={'schemas/axiomiq_interactive_instructional_diagram_interaction_v1.schema.json':'5b8cc1c43a63e21a87ccce134769aee0529e49728b5ecbe43680a1ee18b55c88','schemas/axiomiq_interactive_instructional_diagram_interaction_v1_1.schema.json':'9e10b1da13dfca21f25459ff97d65e45092c02645bf18e232d97ff7a47fa093e','schemas/interaction_formula_registry_v1_1.json':'8b3e8b9acb979d79e6c69768f79233dcceeffba579d14468a03235297a7b2ce9','schemas/interaction_renderer_registry_v1_1.json':'7f743b30995fee70ccc83b1f5deddefa130d3c7af476adf9a0c6ee5d97ff4d67'}
 for rel,digest in expected.items(): assert hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()==digest

def test_v1_fixture_remains_valid_through_dispatch():
 spec=load(V1); sig=spec['linked_procedure_signature']; reg={spec['linked_procedure_id']:{'status':'signed_off','phase_d_sign_off':sig,'procedure':[{} for _ in spec['procedural_step_states']]}}
 assert validate_interaction_spec(spec,procedure_registry=reg).passed

def test_v11_fixture_remains_valid_through_dispatch(): assert validate_interaction_spec(load(V11)).passed
def test_v12_fixture_schema_math_security_and_replay_pass():
 report=validate_interaction_spec(load(V12)); assert report.passed,report.to_dict()

def test_exact_registry_additions_only():
 r11={x['renderer_id'] for x in load('schemas/interaction_renderer_registry_v1_1.json')['entries']}; r12={x['renderer_id'] for x in load('schemas/interaction_renderer_registry_v1_2.json')['entries']}
 f11={x['formula_id'] for x in load('schemas/interaction_formula_registry_v1_1.json')['entries']}; f12={x['formula_id'] for x in load('schemas/interaction_formula_registry_v1_2.json')['entries']}
 assert r12-r11=={'statics_fbd_3d_v1'}; assert f12-f11=={'statics_hydrostatic_center_of_pressure_v1'}
 assert {x['constraint_model_id'] for x in load('schemas/interaction_constraint_model_registry_v1_2.json')['entries']}=={'statics_support_reaction_model_v1','statics_contact_force_model_v1','statics_cable_line_of_action_v1','statics_zero_force_member_rules_v1','statics_pin_action_reaction_pairing_v1'}
 assert {x['display_vocabulary_id'] for x in load('schemas/interaction_display_vocabulary_registry_v1_2.json')['entries']}=={'statics_beam_sign_convention_overlay_v1'}

def test_all_eight_entries_have_complete_typed_contracts():
 docs=[load('schemas/interaction_renderer_registry_v1_2.json')['entries'][-1],load('schemas/interaction_formula_registry_v1_2.json')['entries'][-1],*load('schemas/interaction_constraint_model_registry_v1_2.json')['entries'],*load('schemas/interaction_display_vocabulary_registry_v1_2.json')['entries']]
 assert len(docs)==8
 for x in docs:
  assert x['typed_inputs'] and (x.get('typed_outputs') or x.get('typed_output')); assert x['units_and_dimensions'] if 'units_and_dimensions' in x else x['dimensional_and_unit_rules']; assert x['bounds'] if 'bounds' in x else x['parameter_bounds']; assert x['invariants'] if 'invariants' in x else x['mathematical_invariants']; assert x['deterministic_reference_cases'] and x['negative_cases']; assert x['trusted_beta_implementation_id'].startswith('beta.'); assert x['accessibility_visible_state']['required_labels']

@pytest.mark.parametrize('formula_id',sorted(FORMULA_METADATA))
def test_all_v12_formula_reference_cases(formula_id):
 c=FORMULA_METADATA[formula_id]['deterministic_reference_cases'][0]; assert evaluate_reference_case(formula_id,c['inputs'])==pytest.approx(c['expected'],abs=c['absolute_tolerance'])

def recompute(spec):
 keys=('student_adjustable_variables','available_toggles','dependent_calculated_values','geometric_constraints','mathematical_constraints','procedural_step_states','expected_state_transitions','keyboard_interaction_model','initial_state','reset_state','deterministic_validation_cases'); spec['interaction_fingerprint']=hashlib.sha256(json.dumps({k:spec[k] for k in keys},sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()).hexdigest(); return spec

@pytest.mark.parametrize('kind',('renderer','formula','constraint','vocabulary'))
def test_unknown_registry_identifiers_fail_closed(kind):
 s=load(V12)
 if kind=='renderer': s['renderer_id']='unknown_renderer'
 elif kind=='formula': s['dependent_calculated_values'][-1]['formula_id']='unknown_formula'; recompute(s)
 elif kind=='constraint': s['mathematical_constraints'][0]['constraint_model_id']='unknown_constraint'; recompute(s)
 else: s['visible_labels'][-1]['display_vocabulary_id']='unknown_vocabulary'
 report=validate_interaction_spec(s); assert not report.passed and (report.security_rejections or not report.gate_results[0].passed)

@pytest.mark.parametrize('payload',[{'script':'x'},{'caption':'safe data:image/svg+xml,abc'},{'onclick':'x()'},{'caption':'https://evil.invalid/x'},{'expression':'x+y'}])
def test_security_envelope_remains_fail_closed(payload):
 s=load(V12); s.update(payload); assert validate_interaction_spec(s).security_rejections

def test_hydrostatic_formula_and_negative_domains():
 assert evaluate_formula('statics_hydrostatic_center_of_pressure_v1',{'d':2,'i':4,'a':2},{'centroid_depth':'d','centroidal_area_inertia':'i','area':'a'})==3
 with pytest.raises(FormulaError): evaluate_formula('statics_hydrostatic_center_of_pressure_v1',{'d':0,'i':4,'a':2},{'centroid_depth':'d','centroidal_area_inertia':'i','area':'a'})
 with pytest.raises(FormulaError): evaluate_formula('statics_hydrostatic_center_of_pressure_v1',{'d':2,'i':4,'a':0},{'centroid_depth':'d','centroidal_area_inertia':'i','area':'a'})

def test_package_binds_every_v12_registry_digest():
 d=package_declaration(); assert d['interaction_schema_version']=='1.2.0'; assert validate_package_declaration(d)==[]
 for k in [x for x in d if x.endswith('sha256')]: bad=dict(d); bad[k]='0'*64; assert validate_package_declaration(bad)==[f'{k} mismatch']

def test_compatibility_matrix_declares_all_supported_versions():
 m=load('schemas/interaction_schema_compatibility_matrix_v1_2.json'); assert [x['schema_version'] for x in m['versions']]==['1.0.0','1.1.0','1.2.0']
