"""Closed trusted formula adapter for interaction schema v1.2.0."""
from __future__ import annotations
import json,math
from pathlib import Path
from typing import Any,Mapping
from .formulas_v1_1 import FormulaError,_calculate,_enforce_bounds,_n,_resolved

REGISTRY_PATH=Path(__file__).resolve().parents[2]/'schemas'/'interaction_formula_registry_v1_2.json'
FORMULA_METADATA={x['formula_id']:x for x in json.loads(REGISTRY_PATH.read_text())['entries']}

def _evaluate(meta,ordered):
    if meta['operation']=='hydrostatic_center_of_pressure':
        depth=ordered['centroid_depth']; inertia=ordered['centroidal_area_inertia']; area=ordered['area']; angle=ordered['inclination_angle_deg']
        return depth+inertia*math.sin(math.radians(angle))**2/(depth*area)
    return _calculate(meta['operation'],ordered)

def evaluate_formula(formula_id:str,values:Mapping[str,float],inputs:Mapping[str,Any])->float:
    meta=FORMULA_METADATA.get(formula_id)
    if meta is None: raise FormulaError(f'unsupported formula_id: {formula_id}')
    resolved=_resolved(values,inputs); ordered={x['name']:resolved[x['name']] for x in meta['typed_inputs']}
    _enforce_bounds(meta,ordered); return _n(formula_id,_evaluate(meta,ordered))

def evaluate_reference_case(formula_id:str,inputs:Mapping[str,Any])->float:
    meta=FORMULA_METADATA[formula_id]; ordered={x['name']:([_n(x['name'],v) for v in inputs[x['name']]] if x['type']=='number_list' else _n(x['name'],inputs[x['name']])) for x in meta['typed_inputs']}
    _enforce_bounds(meta,ordered); return _n(formula_id,_evaluate(meta,ordered))
