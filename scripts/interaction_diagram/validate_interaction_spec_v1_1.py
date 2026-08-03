"""Version-dispatching, fail-closed interaction specification validator."""
from __future__ import annotations
import hashlib,json,math,re
from dataclasses import dataclass,field
from pathlib import Path
from typing import Any,Mapping
import jsonschema
from .formulas_v1_1 import FORMULA_METADATA, FormulaError, evaluate_formula
from .validate_interaction_spec import (validate_interaction_spec as validate_v1,compute_diagram_fingerprint,compute_interaction_fingerprint)

ROOT=Path(__file__).resolve().parents[2]
SCHEMA=ROOT/'schemas'/'axiomiq_interactive_instructional_diagram_interaction_v1_1.schema.json'
RENDERERS={x['renderer_id'] for x in json.loads((ROOT/'schemas'/'interaction_renderer_registry_v1_1.json').read_text())['entries']}
FORBIDDEN_KEYS={'script','javascript','__proto__','constructor','eval','expression','expr','code','handler','callback','onclick','onerror','onload','onkeydown','onkeyup'}
FORBIDDEN=(re.compile(r'(?i)<\s*script\b'),re.compile(r'(?i)\bjavascript\s*:'),re.compile(r'(?i)\bdata\s*:'),re.compile(r'(?i)\bhttps?\s*:'),re.compile(r'(?i)\beval\s*\('),re.compile(r'(?i)\bnew\s+Function\b'),re.compile(r'(?i)\bimport\s*\('))
GATES=('schema','procedure_link','diagram_to_text_consistency','mathematical_state','deterministic_replay','variable_bound','reset_state','step_transition')
@dataclass
class GateResult: gate:str; passed:bool; errors:list[str]=field(default_factory=list)
@dataclass
class ValidationReport:
    passed:bool; gate_results:list[GateResult]; security_rejections:list[str]=field(default_factory=list)
    def to_dict(self): return {'passed':self.passed,'security_rejections':self.security_rejections,'gates':[{'gate':x.gate,'passed':x.passed,'errors':x.errors} for x in self.gate_results]}

def _walk(x,path='$'):
    yield path,x
    if isinstance(x,dict):
        for k,v in x.items(): yield from _walk(v,f'{path}.{k}')
    elif isinstance(x,list):
        for i,v in enumerate(x): yield from _walk(v,f'{path}[{i}]')

def security_rejections(spec):
    out=[]
    if not isinstance(spec,dict): return ['spec must be a JSON object']
    if spec.get('renderer_id') not in RENDERERS: out.append(f"unsupported renderer_id: {spec.get('renderer_id')!r}")
    for p,x in _walk(spec):
        if isinstance(x,dict):
            for k in x:
                low=str(k).lower()
                if low in FORBIDDEN_KEYS or (low.startswith('on') and low[2:].isalpha() and len(low)<32): out.append(f'forbidden executable key at {p}.{k}')
        elif isinstance(x,str):
            if any(q.search(x) for q in FORBIDDEN) or x.strip().startswith(('http://','https://','//','javascript:','data:')): out.append(f'forbidden executable or remote value at {p}')
    for c in spec.get('dependent_calculated_values',[]):
        if c.get('formula_id') not in FORMULA_METADATA: out.append(f"unsupported formula_id: {c.get('formula_id')!r}")
        for value in (c.get('inputs') or {}).values():
            if isinstance(value,str) and any(ch in value for ch in '()*/+-%'): out.append(f'unvalidated expression-like input rejected: {value!r}')
    return list(dict.fromkeys(out))

def _eval(spec,variables):
    vals={k:float(v) for k,v in variables.items()}; result={}
    for c in spec.get('dependent_calculated_values',[]):
        vals[c['id']]=evaluate_formula(c['formula_id'],vals,c['inputs']); result[c['id']]=vals[c['id']]
    return result

UNIT_DIMENSIONS={'N':'force','kN':'force','lb':'force','m':'length','mm':'length','cm':'length','ft':'length','in':'length','deg':'angle','rad':'angle','dimensionless':'dimensionless','N*m':'moment','kN*m':'moment','N/m':'force_per_length','kN/m':'force_per_length','m^2':'area','m^3':'volume','m^4':'length_fourth','kg':'mass','kg*m^2':'mass_length_squared','Pa':'pressure','MPa':'pressure'}
CONCRETE_OUTPUTS={'force','moment','length','angle','dimensionless','area','volume','length_fourth','mass_length_squared'}
def _unit_contract_errors(spec):
    errors=[]
    units={x['id']:x['unit'] for x in spec.get('student_adjustable_variables',[])}
    for calc in spec.get('dependent_calculated_values',[]):
        meta=FORMULA_METADATA[calc['formula_id']]; declared=UNIT_DIMENSIONS.get(calc['unit']); expected=meta['typed_output']['dimension']
        if expected in CONCRETE_OUTPUTS and declared!=expected: errors.append(f"{calc['id']} unit dimension {declared} does not match {expected}")
        if expected=='inertia' and declared not in {'length_fourth','mass_length_squared'}: errors.append(f"{calc['id']} must use area or mass inertia units")
        if expected.startswith('same_as'):
            refs=[]
            for value in calc['inputs'].values(): refs.extend(value if isinstance(value,list) else [value])
            input_dims={UNIT_DIMENSIONS.get(units.get(ref)) for ref in refs if units.get(ref)}
            input_dims.discard(None)
            if input_dims and declared not in input_dims: errors.append(f"{calc['id']} output unit does not match input dimension")
        units[calc['id']]=calc['unit']
    return errors

def validate_interaction_spec(spec,*,procedure_registry=None):
    if isinstance(spec,dict) and spec.get('schema_version')=='1.0.0': return validate_v1(spec,procedure_registry=procedure_registry)
    rejects=security_rejections(spec)
    if rejects: return ValidationReport(False,[GateResult(g,False,rejects if g=='schema' else []) for g in GATES],rejects)
    errors={g:[] for g in GATES}
    try: jsonschema.validate(spec,json.loads(SCHEMA.read_text()))
    except Exception as e: errors['schema'].append(str(e))
    try:
        if spec.get('diagram_fingerprint')!=compute_diagram_fingerprint(spec): errors['schema'].append('diagram_fingerprint mismatch')
        payload={key:spec[key] for key in ('student_adjustable_variables','available_toggles','dependent_calculated_values','geometric_constraints','mathematical_constraints','procedural_step_states','expected_state_transitions','keyboard_interaction_model','initial_state','reset_state','deterministic_validation_cases')}
        expected_fingerprint=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()).hexdigest()
        if spec.get('interaction_fingerprint')!=expected_fingerprint: errors['schema'].append('interaction_fingerprint mismatch')
        errors['mathematical_state'].extend(_unit_contract_errors(spec))
    except Exception as e: errors['schema'].append(f'fingerprint failure: {e}')
    if procedure_registry is not None:
        rec=procedure_registry.get(str(spec.get('linked_procedure_id')))
        if not rec: errors['procedure_link'].append('linked procedure absent')
        elif (rec.get('status') or (rec.get('phase_d_sign_off') or {}).get('status'))!='signed_off': errors['procedure_link'].append('linked procedure not signed_off')
    try:
        first=[]; second=[]
        for case in spec.get('deterministic_validation_cases',[]):
            a=_eval(spec,case['input_variables']); b=_eval(spec,case['input_variables']); first.append(a); second.append(b)
            for k,want in case['expected_calculated'].items():
                if not math.isclose(a[k],float(want),rel_tol=0,abs_tol=float(case.get('tolerance',{}).get(k,0))): errors['mathematical_state'].append(f"{case['case_id']}:{k} mismatch")
        if json.dumps(first,sort_keys=True)!=json.dumps(second,sort_keys=True): errors['deterministic_replay'].append('replay divergence')
    except Exception as e: errors['mathematical_state'].append(str(e)); errors['deterministic_replay'].append(str(e))
    meta={v['id']:v for v in spec.get('student_adjustable_variables',[])}
    for state in [spec.get('initial_state',{}),spec.get('reset_state',{})]:
        for k,m in meta.items():
            val=state.get('variables',{}).get(k)
            if val is None or val<m['minimum'] or val>m['maximum']: errors['variable_bound'].append(f'{k} outside bounds')
    if spec.get('reset_state')!=spec.get('initial_state'): errors['reset_state'].append('reset_state must equal initial_state')
    steps=[x['step_id'] for x in spec.get('procedural_step_states',[])]
    trans=spec.get('expected_state_transitions',[])
    if not any(x.get('trigger')=='auto_enter_on_load' for x in trans): errors['step_transition'].append('missing auto_enter_on_load')
    if not any(x.get('trigger')=='student_reset' for x in trans): errors['step_transition'].append('missing student_reset')
    for a,b in zip(steps,steps[1:]):
        if not any(x.get('from_step_id')==a and x.get('to_step_id')==b and x.get('trigger')=='student_next_step' for x in trans): errors['step_transition'].append(f'missing next {a}->{b}')
    gates=[GateResult(g,not errors[g],errors[g]) for g in GATES]
    return ValidationReport(all(x.passed for x in gates),gates,[])
