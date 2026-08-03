"""Closed, trusted formula adapter for interaction schema v1.1.0."""
from __future__ import annotations
import json, math
from pathlib import Path
from typing import Mapping, Any

class FormulaError(ValueError): pass

def _n(name: str, value: object) -> float:
    if isinstance(value,bool) or not isinstance(value,(int,float)): raise FormulaError(f'{name} must be numeric')
    value=float(value)
    if not math.isfinite(value): raise FormulaError(f'{name} must be finite')
    return value

REGISTRY_PATH=Path(__file__).resolve().parents[2]/'schemas'/'interaction_formula_registry_v1_1.json'
FORMULA_METADATA={x['formula_id']:x for x in json.loads(REGISTRY_PATH.read_text())['entries']}

def _resolved(values: Mapping[str,float], inputs: Mapping[str,Any]) -> dict[str,Any]:
    out={}
    for k,v in inputs.items():
        if isinstance(v,list): out[k]=[_n(str(x),values[str(x)]) for x in v]
        else: out[k]=_n(str(v),values[str(v)])
    return out

def _enforce_bounds(meta: Mapping[str,Any], ordered: Mapping[str,Any]) -> None:
    bounds=meta.get('parameter_bounds') or {}
    for name,rule in bounds.items():
        if name=='all_inputs':
            for key,value in ordered.items():
                for item in value if isinstance(value,list) else [value]: _enforce_rule(key,item,rule)
        elif name in ordered and isinstance(rule,dict):
            value=ordered[name]
            for item in value if isinstance(value,list) else [value]: _enforce_rule(name,item,rule)
    if bounds.get('not_both_zero') and all(value==0 for value in ordered.values()): raise FormulaError('vector inputs must not all be zero')
    if 'ratio' in bounds and len(ordered)>=2:
        vals=list(ordered.values())
        if vals[1]==0: raise FormulaError('zero denominator')
        _enforce_rule('ratio',vals[0]/vals[1],bounds['ratio'])
    if 'intensity_sum' in bounds:
        vals=list(ordered.values()); _enforce_rule('intensity_sum',vals[0]+vals[1],bounds['intensity_sum'])

def _enforce_rule(name: str, value: float, rule: Mapping[str,Any]) -> None:
    if 'minimum' in rule and value < rule['minimum']: raise FormulaError(f'{name} below minimum')
    if 'maximum' in rule and value > rule['maximum']: raise FormulaError(f'{name} above maximum')
    if 'exclusiveMinimum' in rule and value <= rule['exclusiveMinimum']: raise FormulaError(f'{name} must exceed minimum')
    if 'notEqual' in rule and value == rule['notEqual']: raise FormulaError(f'{name} has forbidden value')

def _calculate(op: str, a: dict[str,Any]) -> float:
    v=list(a.values())
    if op=='polar_x': return v[0]*math.cos(math.radians(v[1]))
    if op=='polar_y': return v[0]*math.sin(math.radians(v[1]))
    if op=='sum': return sum(v[0] if len(v)==1 and isinstance(v[0],list) else v)
    if op=='subtract': return v[0]-v[1]
    if op=='multiply': return v[0]*v[1]
    if op=='multiply3': return v[0]*v[1]*v[2]
    if op=='half_product': return v[0]*v[1]/2
    if op=='negative': return -v[0]
    if op=='identity': return v[0]
    if op=='half': return v[0]/2
    if op=='two_thirds': return 2*v[0]/3
    if op=='norm2': return math.hypot(v[0],v[1])
    if op=='norm3': return math.sqrt(v[0]**2+v[1]**2+v[2]**2)
    if op=='direction2':
        if v[0]==0 and v[1]==0: raise FormulaError('zero vector direction undefined')
        return math.degrees(math.atan2(v[1],v[0]))%360
    if op=='divide':
        if v[1]==0: raise FormulaError('zero denominator')
        return v[0]/v[1]
    if op=='neg_divide':
        if v[1]==0: raise FormulaError('zero denominator')
        return -v[0]/v[1]
    if op=='acos_ratio':
        if v[1]<=0: raise FormulaError('norm must be positive')
        ratio=v[0]/v[1]
        if ratio < -1-1e-12 or ratio > 1+1e-12: raise FormulaError('acos ratio outside [-1,1]')
        return math.degrees(math.acos(max(-1,min(1,ratio))))
    if op=='dot2': return v[0]*v[2]+v[1]*v[3]
    if op=='dot3': return v[0]*v[3]+v[1]*v[4]+v[2]*v[5]
    if op=='cross_x' or op=='cross_y' or op=='cross_z': return v[0]*v[3]-v[1]*v[2]
    if op=='moment2': return v[0]*v[3]-v[1]*v[2]
    if op=='trapezoid_area': return (v[0]+v[1])*v[2]/2
    if op=='trapezoid_centroid':
        if v[0]+v[1]==0: raise FormulaError('zero total intensity')
        return v[2]*(v[0]+2*v[1])/(3*(v[0]+v[1]))
    if op=='clamp_abs': return math.copysign(min(abs(v[0]),v[1]),v[0])
    if op=='exp_product': return math.exp(v[0]*v[1])
    if op=='parallel_axis': return v[0]+v[1]*v[2]**2
    if op=='sqrt_ratio':
        if v[0]<0 or v[1]<=0: raise FormulaError('invalid square-root ratio domain')
        return math.sqrt(v[0]/v[1])
    if op=='rectangle_inertia': return v[0]*v[1]**3/12
    if op=='circle_inertia': return math.pi*v[0]**4/4
    if op=='rod_inertia': return v[0]*v[1]**2/12
    if op=='disk_inertia': return v[0]*v[1]**2/2
    raise FormulaError(f'unimplemented trusted operation: {op}')

def evaluate_formula(formula_id: str, values: Mapping[str,float], inputs: Mapping[str,Any]) -> float:
    meta=FORMULA_METADATA.get(formula_id)
    if meta is None: raise FormulaError(f'unsupported formula_id: {formula_id}')
    resolved=_resolved(values,inputs)
    ordered={x['name']:resolved[x['name']] for x in meta['typed_inputs']}
    _enforce_bounds(meta,ordered)
    return _n(formula_id,_calculate(meta['operation'],ordered))

def evaluate_reference_case(formula_id: str, inputs: Mapping[str,float]) -> float:
    meta=FORMULA_METADATA[formula_id]
    ordered={x['name']:([_n(x['name'],v) for v in inputs[x['name']]] if x['type']=='number_list' else _n(x['name'],inputs[x['name']])) for x in meta['typed_inputs']}
    _enforce_bounds(meta,ordered)
    return _n(formula_id,_calculate(meta['operation'],ordered))
