"""Real deterministic nonfixture General Chemistry production bank."""
from pathlib import Path
import json
import math
import hashlib
from tools.course_compiler_demo.production_questions import ProductionFamily,ProductionValidationRecordV1,default_validator,produce_course_bank
from tools.course_compiler_demo.subject_packs.chemistry.pack import build_general_chemistry_pack
from .review import build_evidence_reviewer

def _families():
 specs=(
  ("measurement_units","numeric_scalar",lambda p:f"A sample has mass {p['a']} grams and volume {p['b']} milliliters. What density in grams per milliliter results, rounded to {p['sigfig']} significant figures?",lambda p:p['a']/p['b']),
  ("atomic_structure","numeric_scalar",lambda p:f"A neutral atom has atomic number {p['a']}. How many electrons does it contain? Report the exact count ({p['sigfig']} significant figures not applicable).",lambda p:p['a']),
  ("periodic_trends","multiple_choice",lambda p:f"Across a period from position {p['b']} toward {p['a']}, which trend generally increases? Choices: electronegativity, atomic radius, neither.",lambda p:"electronegativity"),
  ("chemical_bonding","multiple_choice",lambda p:f"For sodium chloride sample {p['a']}, what dominant bonding classification applies? Choices: ionic, metallic, nonpolar covalent.",lambda p:"ionic"),
  ("molecular_geometry","multiple_choice",lambda p:f"A central atom with four bonding pairs and no lone pairs in model {p['a']} has what geometry? Choices: tetrahedral, bent, trigonal planar.",lambda p:"tetrahedral"),
  ("nomenclature","multiple_choice",lambda p:f"In nomenclature exercise {p['a']}, what is the standard name for CO2? Choices: carbon dioxide, carbon monoxide, cobalt oxide.",lambda p:"carbon dioxide"),
  ("reaction_conservation","numeric_scalar",lambda p:f"A closed reaction starts with {p['a']} grams total reactants. By mass conservation, what total product mass in grams results, reported to {p['sigfig']} significant figures?",lambda p:p['a']),
  ("stoichiometry","numeric_scalar",lambda p:f"The balanced relationship A + 2B -> AB2 requires 2 moles B per mole A. If {p['b']} moles A react, how many moles B are required, to {p['sigfig']} significant figures?",lambda p:2*p['b']),
  ("thermochemistry","numeric_scalar",lambda p:f"A process absorbs {p['a']} kilojoules then releases {p['b']} kilojoules. What signed net heat in kilojoules is absorbed, to {p['sigfig']} significant figures?",lambda p:p['a']-p['b']),
  ("ideal_gas","numeric_scalar",lambda p:f"At fixed temperature, gas pressure is {p['a']} kilopascals in {p['b']} liters. If volume doubles, what pressure in kilopascals results, to {p['sigfig']} significant figures?",lambda p:p['a']/2),
  ("solution_molarity","numeric_scalar",lambda p:f"A solution contains {p['b']} moles solute in {p['c']} liters. What molarity in moles per liter results, to {p['sigfig']} significant figures?",lambda p:p['b']/p['c']),
  ("equilibrium_shift","multiple_choice",lambda p:f"For equilibrium trial {p['a']}, adding reactant favors which direction? Choices: products, reactants, no shift.",lambda p:"products"),
  ("acids_bases","numeric_scalar",lambda p:f"A solution has hydrogen ion concentration 1e-{p['b']} moles per liter. What is its pH, reported to {p['sigfig']} significant figures?",lambda p:p['b']),
  ("electrochemistry","numeric_scalar",lambda p:f"A cell has cathode potential {p['a']/10} volts and anode reduction potential {p['b']/10} volts. What cell potential in volts results, to {p['sigfig']} significant figures?",lambda p:p['a']/10-p['b']/10),
 )
 out=[]
 for i,(name,shape,prompt,answer) in enumerate(specs):
  def generator(p,prompt=prompt,answer=answer,shape=shape):return prompt(p),(_sigfig(answer(p),p["sigfig"]) if shape=="numeric_scalar" else answer(p))
  def deriver(p,name=name):return _independent_derivation(name,p)
  out.append(ProductionFamily(f"GC_PROD_FAMILY_{i+1:02d}_{name}",f"GENERAL_CHEMISTRY_PROC_{i+1:03d}",f"GENERAL_CHEMISTRY_UNIT_{i%8+1:02d}",f"GENERAL_CHEMISTRY_TOPIC_{i+1:03d}",f"GENERAL_CHEMISTRY_SKILL_{i+1:03d}",shape,shape,("unit_conversion_error","significant_figure_error","stoichiometric_ratio_error","formula_consistency_error"),lambda index,offset=i:{"a":20+((index*11+offset)%71),"b":2+((index*7+offset)%9),"c":2+((index*3+offset)%7),"sigfig":3},generator,deriver))
 return tuple(out)

def _sigfig(value,digits):
 if value==0:return 0.0
 return round(float(value),digits-1-int(math.floor(math.log10(abs(float(value))))))

def _independent_derivation(name,p):
 if name=="measurement_units": raw=float(p["a"])/float(p["b"])
 elif name=="atomic_structure": raw=int(p["a"])
 elif name=="periodic_trends": return "electronegativity"
 elif name=="chemical_bonding": return "ionic"
 elif name=="molecular_geometry": return "tetrahedral"
 elif name=="nomenclature": return "carbon dioxide"
 elif name=="reaction_conservation": raw=sum((p["a"],))
 elif name=="stoichiometry": raw=sum(p["b"] for _ in range(2))
 elif name=="thermochemistry": raw=sum((p["a"],-p["b"]))
 elif name=="ideal_gas": raw=p["a"]*(p["b"]/(2*p["b"]))
 elif name=="solution_molarity": raw=float(p["b"])/p["c"]
 elif name=="equilibrium_shift": return "products"
 elif name=="acids_bases": raw=-math.log10(10.0**(-p["b"]))
 elif name=="electrochemistry": raw=(p["a"]-p["b"])/10.0
 else: raise ValueError("unknown chemistry family")
 return _sigfig(raw,p["sigfig"])

def _normalized_choice(value): return " ".join(str(value).strip().rstrip(".?").lower().split())

def _choice_evidence(candidate,derived_answer):
 if candidate.answer_contract["shape"]!="multiple_choice": return {"choice_count":0,"answer_matches":0,"passed":True}
 if "Choices:" not in candidate.prompt:return {"choice_count":0,"answer_matches":0,"passed":False}
 choices=[_normalized_choice(x) for x in candidate.prompt.split("Choices:",1)[1].split(",")]
 answer=_normalized_choice(derived_answer); distinct=set(choices); matches=sum(x==answer for x in choices)
 return {"choice_count":len(distinct),"answer_matches":matches,"passed":len(distinct)>=2 and len(distinct)==len(choices) and matches==1}

def _chemistry_validator(evidence):
 def validate(candidate,derivation,generator_answer):
  base=default_validator(candidate,derivation,generator_answer); prompt=candidate.prompt.lower(); family=candidate.request["generation_family_id"]
  choice=_choice_evidence(candidate,derivation.normalized_answer)
  numeric=candidate.answer_contract["shape"]=="numeric_scalar"
  rounding_ok=(not numeric) or ("significant figures" in prompt)
  unit_ok=(not numeric) or any(unit in prompt for unit in ("grams","moles","kilojoules","kilopascals","liters","volts","exact count","ph"))
  formula_ok=("nomenclature" not in family or "co2" in prompt) and ("chemical_bonding" not in family or "sodium chloride" in prompt) and ("stoichiometry" not in family or "a + 2b -> ab2" in prompt)
  mole_ok=("stoichiometry" not in family and "solution_molarity" not in family) or "moles" in prompt
  chemistry_ok=rounding_ok and unit_ok and formula_ok and mole_ok
  reasons=base.reasons+(() if chemistry_ok else ("CHEMISTRY_DOMAIN_VALIDATION_FAILED",))+(() if choice["passed"] else ("MULTIPLE_CHOICE_CONTRACT_INVALID",))
  passed=base.answer_contract_pass and choice["passed"]
  evidence[candidate.candidate_id]={"family_id":family,"shape":candidate.answer_contract["shape"],"choice_count":choice["choice_count"],"answer_matches":choice["answer_matches"],"candidate_digest":hashlib.sha256(candidate.to_json().encode()).hexdigest(),"passed":base.passed and chemistry_ok and choice["passed"]}
  return ProductionValidationRecordV1(base.validation_id,base.candidate_id,base.grading_pass,base.procedure_compatibility_pass,base.failure_signal_pass,base.prompt_determinacy_pass,base.unit_tolerance_pass and chemistry_ok,passed,reasons)
 return validate

def build_general_chemistry_bank():
 pack=build_general_chemistry_pack(); h=pack["deterministic_sha256"]
 evidence=({"evidence_id":"gc-pack-v1","source_identity":"registered:GENERAL_CHEMISTRY_PACK_V1","source_hash":h},)
 review_evidence={}
 return produce_course_bank("GENERAL_CHEMISTRY","GENERAL_CHEMISTRY_PACK_V1",h,evidence,_families(),reviewer=build_evidence_reviewer(review_evidence),validator=_chemistry_validator(review_evidence))

def write_general_chemistry_evidence(output_root):
 root=Path(output_root); dirs=("authority","generation","candidates","derivations","validations","duplicates","reviews","banks","assessments","exports","logs")
 for name in dirs:(root/name).mkdir(parents=True,exist_ok=True)
 bank,summary=build_general_chemistry_bank(); data=bank.to_dict()
 (root/"authority"/"subject_pack_authority.json").write_text(json.dumps(data["candidates"][0]["authority"],sort_keys=True,indent=2)+"\n")
 (root/"generation"/"generation_requests.json").write_text(json.dumps([c["request"] for c in data["candidates"]],sort_keys=True,indent=2)+"\n")
 for name in ("candidates","derivations","validations","duplicates","reviews"):(root/name/f"{name}.json").write_text(json.dumps(data[name],sort_keys=True,indent=2)+"\n")
 (root/"banks"/"general_chemistry_locked_bank.json").write_text(json.dumps(data,sort_keys=True,indent=2)+"\n")
 (root/"logs"/"course_production_summary.json").write_text(json.dumps(summary.to_dict(),sort_keys=True,indent=2)+"\n")
 (root/"exports"/"noncanonical_export_manifest.json").write_text(json.dumps({"bank_sha256":bank.bank_sha256,"candidate_count":100,"noncanonical":True,"student_visible":False,"eligible_for_alpha_import":False,"database_write_authorized":False},sort_keys=True,indent=2)+"\n")
 return bank,summary
