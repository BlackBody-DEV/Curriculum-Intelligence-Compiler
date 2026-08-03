import copy, hashlib, json
from pathlib import Path
import jsonschema, pytest
from scripts.interaction_diagram.formulas_v1_1 import FORMULA_METADATA, FormulaError, evaluate_formula, evaluate_reference_case
from scripts.interaction_diagram.package_contract import package_declaration, schema_sha256, validate_package_declaration
from scripts.interaction_diagram.validate_interaction_spec_v1_1 import validate_interaction_spec

ROOT=Path(__file__).resolve().parents[2]
V1=ROOT/'schemas/axiomiq_interactive_instructional_diagram_interaction_v1.schema.json'
V11=ROOT/'schemas/axiomiq_interactive_instructional_diagram_interaction_v1_1.schema.json'
FIX1=ROOT/'fixtures/interaction_diagrams/vectors_component_resolution_and_addition_explanation_v1.json'
FIX11=ROOT/'fixtures/interaction_diagrams/vectors_component_resolution_and_addition_explanation_v1_1.json'

def load(p): return json.loads(p.read_text())

def test_audited_v1_baseline_is_byte_exact_and_schema_valid():
    assert hashlib.sha256(V1.read_bytes()).hexdigest()=='5b8cc1c43a63e21a87ccce134769aee0529e49728b5ecbe43680a1ee18b55c88'
    jsonschema.validate(load(FIX1),load(V1))

def test_v1_dispatch_remains_valid():
    spec=load(FIX1); sig=spec['linked_procedure_signature']; steps=[{} for _ in spec['procedural_step_states']]
    registry={spec['linked_procedure_id']:{'status':'signed_off','phase_d_sign_off':sig,'procedure':steps}}
    assert validate_interaction_spec(spec,procedure_registry=registry).passed

def test_v11_fixture_schema_math_and_replay_pass():
    report=validate_interaction_spec(load(FIX11))
    assert report.passed, report.to_dict()

def test_registry_metadata_is_complete_and_closed():
    assert len(FORMULA_METADATA)==53
    for key,item in FORMULA_METADATA.items():
        assert item['formula_id']==key
        assert item['typed_inputs'] and item['typed_output']
        assert item['dimensional_and_unit_rules'] and item['parameter_bounds']
        assert item['mathematical_invariants']
        assert item['deterministic_reference_cases'] and item['negative_cases']
        assert item['trusted_beta_implementation_id'].startswith('beta.interaction_math.')

@pytest.mark.parametrize('formula_id',sorted(FORMULA_METADATA))
def test_all_formula_reference_cases(formula_id):
    case=FORMULA_METADATA[formula_id]['deterministic_reference_cases'][0]
    actual=evaluate_reference_case(formula_id,case['inputs'])
    assert actual==pytest.approx(case['expected'],abs=case['absolute_tolerance'])

@pytest.mark.parametrize('bad',[
    {'script':'alert(1)'},{'onclick':'doThing()'},{'caption':'https://evil.invalid/x'},
    {'expression':'x+y'},{'javascript':'eval(x)'},
])
def test_executable_and_remote_surfaces_rejected(bad):
    spec=load(FIX11); spec.update(bad)
    report=validate_interaction_spec(spec)
    assert not report.passed and report.security_rejections

def test_unknown_renderer_and_formula_fail_closed():
    spec=load(FIX11); spec['renderer_id']='untrusted_renderer'
    assert validate_interaction_spec(spec).security_rejections
    spec=load(FIX11); spec['dependent_calculated_values'][0]['formula_id']='free_form_math'
    assert validate_interaction_spec(spec).security_rejections

def test_expression_smuggling_rejected():
    spec=load(FIX11); spec['dependent_calculated_values'][0]['inputs']['magnitude']='F_A_mag*2'
    assert validate_interaction_spec(spec).security_rejections

def test_package_declaration_is_exact_and_digest_reproduces():
    declaration=package_declaration()
    assert declaration['interaction_schema_id']=='axiomiq_interactive_instructional_diagram_interaction_v1'
    assert declaration['interaction_schema_version']=='1.1.0'
    assert declaration['interaction_schema_sha256']==hashlib.sha256(V11.read_bytes()).hexdigest()==schema_sha256()
    assert validate_package_declaration(declaration)==[]
    bad=dict(declaration,interaction_schema_version='1.0.0')
    assert validate_package_declaration(bad)==['interaction_schema_version mismatch']

def test_schema_envelope_remains_closed():
    spec=load(FIX11); spec['unexpected_property']=1
    with pytest.raises(jsonschema.ValidationError): jsonschema.validate(spec,load(V11))

def test_zero_denominator_is_rejected_by_trusted_adapter():
    with pytest.raises(FormulaError): evaluate_formula('unit_vector_component',{'component':1,'norm':0},{'component':'component','norm':'norm'})
