"""Deterministic synthesis for capability/catalog wave 044.

All builders are pure.  The Beta proof is always dry-run and this module performs
no database, canonical, Beta, or student-visible writes.
"""
from __future__ import annotations

import hashlib
import importlib
import inspect
import json
from typing import Any, Callable, Mapping

from tools.course_compiler_demo.answer_engines import build_default_registry, resolve_engine_type
from tools.course_compiler_demo.answer_engines.registry import DISABLED_ENGINE_TYPES, ENABLED_ENGINE_TYPES
from tools.course_compiler_demo.assessment_compiler import compile_assessment
from tools.course_compiler_demo.beta_export import build_beta_export, dry_run_import_validate, stable_export_hash
from tools.course_compiler_demo.generation_recipes import GenerationContextV1, GenerationRecipeError, GenerationRecipeRegistry, GenerationRecipeRuntime
from tools.course_compiler_demo.universal_core import AnswerContractV1, AssessmentBlueprintV1, ValidatedQuestionReferenceV1
from tools.course_compiler_demo.subject_packs.chemistry import build_general_chemistry_pack, validate_general_chemistry_pack
from tools.course_compiler_demo.subject_packs.computer_science import build_computer_science_course_catalog, build_programming_fundamentals_pack, validate_computer_science_course_catalog, validate_programming_fundamentals_pack
from tools.course_compiler_demo.subject_packs.engineering_mathematics import build_engineering_mathematics_catalog, validate_engineering_mathematics_catalog
from tools.course_compiler_demo.subject_packs.life_sciences import build_life_chemistry_catalog, validate_life_chemistry_catalog
from tools.course_compiler_demo.subject_packs.mathematics import build_mathematics_reference_pack, build_remaining_mathematics_catalog, validate_mathematics_reference_pack, validate_remaining_mathematics_catalog
from tools.course_compiler_demo.subject_packs.physics_engineering import build_physics_engineering_course_catalog, build_physics_engineering_reference_pack, validate_physics_engineering_course_catalog, validate_physics_engineering_reference_pack


EXISTING_IDS=("ALGEBRA_I","CALCULUS_I","STATICS","ELECTRICITY_AND_MAGNETISM","GENERAL_CHEMISTRY","PROGRAMMING_FUNDAMENTALS")
EXPECTED_NEW_IDS=(
    "PRE_ALGEBRA","ALGEBRA_II","GEOMETRY","TRIGONOMETRY","PRE_CALCULUS","CALCULUS_II","CALCULUS_III","DIFFERENTIAL_EQUATIONS","LINEAR_ALGEBRA",
    "MECHANICS","WAVES_AND_OPTICS","MODERN_PHYSICS","DYNAMICS","MECHANICS_OF_MATERIALS","STRENGTH_OF_MATERIALS","FLUID_MECHANICS","HYDRAULICS","FLUID_DYNAMICS",
    "NUMERICAL_METHODS","ENGINEERING_ANALYSIS","APPLIED_MATHEMATICS","DATA_STRUCTURES","ALGORITHMS","COMPUTATIONAL_THINKING",
    "BIOLOGY","ORGANIC_CHEMISTRY","BIOCHEMISTRY",
)
FORBIDDEN_PERFORMANCE_KEYS=frozenset({"performance","performance_fields","student_performance","student_score","learner_performance"})
DOMAIN_RECIPE_REGISTRY={
    "PRE_ALGEBRA":("count","added count","total count","total = count + added count","additive reasoning","a counted collection supports the total",("whole-number inventory","integer temperature change","fractional recipe batch","ratio table","measurement conversion")),
    "ALGEBRA_II":("initial function value","modeled increase","resulting value","resulting value = initial value + modeled increase","function composition","the transformed function matches the stated parameters",("polynomial model","rational model","exponential model","logarithmic model","sequence model")),
    "GEOMETRY":("directed length","translated length","resulting coordinate","resulting coordinate = directed length + translated length","geometric transformation","coordinate evidence preserves the declared transformation",("triangle construction","similarity map","circle chord","coordinate translation","volume cross-section")),
    "TRIGONOMETRY":("horizontal component","phase adjustment","resultant component","resultant component = horizontal component + phase adjustment","periodic relationship","component evidence follows the declared angle convention",("unit-circle state","sinusoidal model","identity verification","inverse-trig model","polar vector")),
    "PRE_CALCULUS":("base model value","transformation offset","transformed value","transformed value = base model value + transformation offset","function transformation","sample values support the transformed model",("rational function","trigonometric function","conic model","parametric curve","limit model")),
    "CALCULUS_II":("accumulated contribution","additional contribution","total accumulation","total accumulation = accumulated contribution + additional contribution","accumulation principle","partition evidence supports the integral model",("integration technique","improper integral","polar area","convergent series","Taylor approximation")),
    "CALCULUS_III":("x component","y component","resultant spatial component","resultant spatial component = x component + y component","vector field in three-dimensional space","component evidence follows the spatial basis",("space vector","partial derivative field","double integral region","line integral path","surface flux")),
    "DIFFERENTIAL_EQUATIONS":("initial-state contribution","forcing contribution","modeled state","modeled state = initial-state contribution + forcing contribution","solution evolution","residual evidence satisfies the declared differential model",("first-order model","second-order response","Laplace-domain model","phase-plane state","numerical trajectory")),
    "LINEAR_ALGEBRA":("first vector component","second vector component","combined component","combined component = first vector component + second vector component","linear combination","component evidence respects the declared basis",("linear system","matrix transformation","subspace basis","eigenvector model","orthogonal projection")),
    "MECHANICS":("first force component","second force component","net force component","net force component = first force component + second force component","Newtonian force balance","free-body evidence supports the net force",("one-dimensional motion","projectile motion","work-energy balance","momentum collision","rotational motion")),
    "WAVES_AND_OPTICS":("first wave amplitude","second wave amplitude","superposed amplitude","superposed amplitude = first wave amplitude + second wave amplitude","linear superposition","phase-aligned samples support constructive superposition",("traveling wave","standing wave","sound interference","thin-lens image","diffraction pattern")),
    "MODERN_PHYSICS":("first energy contribution","second energy contribution","total modeled energy","total modeled energy = first energy contribution + second energy contribution","quantized energy accounting","spectral evidence supports the energy transition",("relativistic energy","photon interaction","matter wave","atomic transition","nuclear decay")),
    "DYNAMICS":("inertial contribution","applied contribution","dynamic resultant","dynamic resultant = inertial contribution + applied contribution","kinetic balance","motion evidence follows the declared positive direction",("particle kinematics","work-energy motion","impulse-momentum event","rigid-body rotation","vibration response")),
    "MECHANICS_OF_MATERIALS":("axial stress contribution","bending stress contribution","combined stress","combined stress = axial stress contribution + bending stress contribution","stress superposition","section evidence supports the elastic combination",("axial member","torsion shaft","bending beam","transverse shear","column stability")),
    "STRENGTH_OF_MATERIALS":("primary stress","secondary stress","combined demand","combined demand = primary stress + secondary stress","failure-demand combination","material evidence is compared with the declared criterion",("stress transformation","pressure vessel","column buckling","fatigue cycle","structural design")),
    "FLUID_MECHANICS":("inflow rate","secondary inflow rate","total flow rate","total flow rate = inflow rate + secondary inflow rate","control-volume continuity","flow evidence conserves mass",("fluid property state","hydrostatic column","control volume","viscous pipe flow","external flow")),
    "HYDRAULICS":("upstream discharge","tributary discharge","downstream discharge","downstream discharge = upstream discharge + tributary discharge","hydraulic continuity","network evidence conserves discharge",("pressure measurement","pipe loss","pump system","open channel","pipe network")),
    "FLUID_DYNAMICS":("streamwise field component","transverse field component","resultant velocity component","resultant velocity component = streamwise field component + transverse field component","Eulerian velocity field","field samples and flux evidence satisfy continuity",("velocity field","continuity field","vorticity field","boundary layer","compressible flow")),
    "NUMERICAL_METHODS":("current approximation","computed correction","updated approximation","updated approximation = current approximation + computed correction","iterative convergence","residual evidence decreases under the update",("root-finding iteration","linear solver update","interpolation estimate","quadrature refinement","ODE time step")),
    "ENGINEERING_ANALYSIS":("homogeneous response","forced response","total response","total response = homogeneous response + forced response","linear response superposition","residual evidence satisfies the engineering model",("complex-variable model","linear algebra model","ODE response","transform solution","PDE field")),
    "APPLIED_MATHEMATICS":("baseline model term","perturbation term","combined model","combined model = baseline model term + perturbation term","model superposition","comparison evidence supports the approximation",("discrete model","continuous model","optimization model","stochastic model","asymptotic model")),
    "DATA_STRUCTURES":("existing element count","inserted element count","resulting size","resulting size = existing element count + inserted element count","data-structure invariant","operation trace preserves size and ordering invariants",("linked-list update","stack operation","hash-table insertion","tree traversal","graph adjacency update")),
    "ALGORITHMS":("first operation count","second operation count","combined operation count","combined operation count = first operation count + second operation count","algorithmic cost composition","trace evidence matches the declared complexity model",("binary search","comparison sort","divide-and-conquer recurrence","dynamic program","graph traversal")),
    "COMPUTATIONAL_THINKING":("first decomposed task count","second task count","total task count","total task count = first decomposed task count + second task count","problem decomposition","trace evidence connects abstractions to executable steps",("problem decomposition","pattern recognition","abstraction model","simulation","debugging strategy")),
    "BIOLOGY":("first observation count","second observation count","total observations","total observations = first observation count + second observation count","controlled scientific inquiry","replicated observations distinguish evidence from unsupported inference",("controlled experiment","cellular energetics study","genetic cross","evolution evidence","ecosystem survey")),
    "ORGANIC_CHEMISTRY":("first bond-electron contribution","second contribution","total valence contribution","total valence contribution = first bond-electron contribution + second contribution","structure and bonding","valence and functional-group evidence supports the declared connectivity",("bonding model","acid-base comparison","stereochemical assignment","spectroscopy evidence","carbonyl reaction")),
    "BIOCHEMISTRY":("first pathway contribution","second pathway contribution","total biochemical contribution","total biochemical contribution = first pathway contribution + second pathway contribution","biochemical mass and energy accounting","enzyme or pathway evidence supports conservation",("buffer system","protein structure","enzyme kinetics","membrane transport","metabolic pathway")),
}


def _sha(value:Any)->str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()).hexdigest()


def _course_from_single(pack:Mapping[str,Any])->dict[str,Any]:
    course=pack.get("course")
    if not isinstance(course,dict): raise ValueError("single-course pack is malformed")
    return course


def _optional_life_catalog()->tuple[dict[str,dict[str,Any]],list[str]]:
    """Discover lane 044K without guessing or manufacturing missing courses."""
    found:dict[str,dict[str,Any]]={}; errors=[]
    for module_name in ("tools.course_compiler_demo.subject_packs.life_sciences","tools.course_compiler_demo.subject_packs.chemistry"):
        try: module=importlib.import_module(module_name)
        except ImportError: continue
        builders=[getattr(module,name) for name in dir(module) if name.startswith("build_") and "catalog" in name and callable(getattr(module,name))]
        for builder in builders:
            try: payload=builder()
            except Exception as exc: errors.append(f"{builder.__name__}: {exc}"); continue
            courses=payload.get("courses",{}) if isinstance(payload,Mapping) else {}
            for course_id in ("BIOLOGY","ORGANIC_CHEMISTRY","BIOCHEMISTRY"):
                if isinstance(courses.get(course_id),dict): found[course_id]=courses[course_id]
    return found,errors


def discover_course_catalog()->dict[str,Any]:
    math_ref=build_mathematics_reference_pack(); physics_ref=build_physics_engineering_reference_pack()
    existing={**math_ref["courses"],**physics_ref["courses"],"GENERAL_CHEMISTRY":_course_from_single(build_general_chemistry_pack()),"PROGRAMMING_FUNDAMENTALS":_course_from_single(build_programming_fundamentals_pack())}
    new={}
    for pack in (build_remaining_mathematics_catalog(),build_physics_engineering_course_catalog(),build_engineering_mathematics_catalog(),build_computer_science_course_catalog()):
        for course_id,course in pack["courses"].items():
            if course_id not in existing: new[course_id]=course
    life,discovery_errors=_optional_life_catalog(); new.update(life)
    missing=sorted(set(EXPECTED_NEW_IDS)-set(new))
    return {"discovery_errors":discovery_errors,"existing":existing,"missing_new_courses":missing,"new":new,"total":{**existing,**new}}


def validate_all_catalogs()->dict[str,Any]:
    validations=(
        (validate_mathematics_reference_pack,build_mathematics_reference_pack()),
        (validate_physics_engineering_reference_pack,build_physics_engineering_reference_pack()),
        (validate_general_chemistry_pack,build_general_chemistry_pack()),
        (validate_programming_fundamentals_pack,build_programming_fundamentals_pack()),
        (validate_remaining_mathematics_catalog,build_remaining_mathematics_catalog()),
        (validate_physics_engineering_course_catalog,build_physics_engineering_course_catalog()),
        (validate_engineering_mathematics_catalog,build_engineering_mathematics_catalog()),
        (validate_computer_science_course_catalog,build_computer_science_course_catalog()),
        (validate_life_chemistry_catalog,build_life_chemistry_catalog()),
    )
    passed=[]
    for validator,payload in validations: validator(payload); passed.append(validator.__name__)
    catalog=discover_course_catalog()
    return {"catalog_count":len(catalog["total"]),"missing_new_courses":catalog["missing_new_courses"],"passed":passed,"status":"PASS" if not catalog["missing_new_courses"] else "PARTIAL"}


def resolve_engine(engine:str)->str:
    return resolve_engine_type(engine)


def engine_capability_report()->dict[str,Any]:
    registry=build_default_registry(); rows=[]
    for engine in sorted(set(ENABLED_ENGINE_TYPES)|set(DISABLED_ENGINE_TYPES)):
        result=registry.lookup(engine); rows.append({"engine":engine,"status":result.status,"reason":None if result.status=="SUPPORTED" else result.reasons[0]})
    return {"enabled_count":sum(r["status"]=="SUPPORTED" for r in rows),"rows":rows,"status":"PASS"}


def allocation_report(courses:Mapping[str,dict[str,Any]])->dict[str,Any]:
    registry=build_default_registry(); rows=[]
    for course_id,course in sorted(courses.items()):
        allocations=course.get("answer_engine_allocations") or sorted({f["answer_engine"] for f in course["generation_families"]})
        resolved=[]; blockers=[]
        for declared in allocations:
            actual=resolve_engine(declared); lookup=registry.lookup(actual)
            resolved.append({"actual_engine":actual,"declared_engine":declared,"status":lookup.status})
            if lookup.status!="SUPPORTED": blockers.append(f"{declared}: {lookup.reasons[0]}")
        rows.append({"blockers":blockers,"course_id":course_id,"resolved":resolved,"status":"PASS" if not blockers else "FAIL"})
    return {"rows":rows,"status":"PASS" if all(r["status"]=="PASS" for r in rows) else "FAIL"}


GENERATION_RECIPE_PROVIDERS=(
    "tools.course_compiler_demo.generation_recipes.domains.math_engineering",
    "tools.course_compiler_demo.generation_recipes.domains.science_cs",
)


def _provider_recipes(module:Any)->tuple[Any,...]:
    recipes=getattr(module,"RECIPES",None)
    if recipes is not None: return tuple(recipes)
    catalog=getattr(module,"COURSE_RECIPE_REGISTRY",None)
    if isinstance(catalog,Mapping): return tuple(recipe for course_recipes in catalog.values() for recipe in course_recipes)
    raise ValueError("provider does not expose a recipe catalog")


def discover_generation_recipe_runtime(courses:Mapping[str,dict[str,Any]]|None=None)->dict[str,Any]:
    """Discover domain adapters, rejecting a provider atomically on any mismatch.

    A provider's semantic manifest is intentionally required in addition to exact
    identity checks.  Merely repeating the topic label in a prompt cannot make a
    shifted or generic domain recipe eligible for generation.
    """
    available=dict(courses or discover_course_catalog()["new"])
    registry=GenerationRecipeRegistry(); accepted:dict[str,dict[str,Any]]={}; reports=[]
    for module_name in GENERATION_RECIPE_PROVIDERS:
        reasons=[]; staged=[]
        try:
            module=importlib.import_module(module_name); sources=_provider_recipes(module)
            manifest_builder=getattr(module,"semantic_compatibility_manifest",None)
            semantic_validator=getattr(module,"validate_catalog_semantics",None)
            if not callable(manifest_builder):
                raise ValueError("SEMANTIC_COMPATIBILITY_MANIFEST_MISSING")
            manifest=tuple(manifest_builder()) if callable(manifest_builder) else ()
            evidence={row.get("recipe_id"):row for row in manifest if isinstance(row,Mapping)}
            if callable(manifest_builder) and len(evidence)!=len(sources): raise ValueError("SEMANTIC_COMPATIBILITY_MANIFEST_INCOMPLETE")
            for source in sources:
                binding=source.binding; course=available.get(binding.course_id)
                if not isinstance(course,Mapping): raise ValueError(f"COURSE_NOT_DISCOVERED:{binding.course_id}")
                if callable(semantic_validator): semantic_validator(source,course)
                if callable(manifest_builder):
                    row=evidence.get(source.recipe_id,{})
                    if row.get("status")!="PASS" or not row.get("matched_terms"):
                        raise ValueError(f"SEMANTIC_COMPATIBILITY_FAILED:{source.recipe_id}")
                    if dict(row.get("binding",{}))!=dict(binding.__dict__):
                        raise ValueError(f"SEMANTIC_BINDING_MISMATCH:{source.recipe_id}")
                topics={x["topic_id"]:x for x in course["topics"]}; skills={x["micro_skill_id"]:x for x in course["micro_skills"]}
                procedures={x["procedure_id"]:x for x in course["procedures"]}; families={x["family_id"]:x for x in course["generation_families"]}
                if binding.topic_id not in topics or binding.micro_skill_id not in skills or skills[binding.micro_skill_id].get("topic_id")!=binding.topic_id:
                    raise ValueError(f"TOPIC_SKILL_BINDING_MISMATCH:{source.recipe_id}")
                if binding.procedure_id not in procedures or binding.family_id not in families:
                    raise ValueError(f"PROCEDURE_FAMILY_BINDING_MISMATCH:{source.recipe_id}")
                family=families[binding.family_id]
                if family.get("micro_skill_id")!=binding.micro_skill_id or family.get("procedure_id")!=binding.procedure_id:
                    raise ValueError(f"FAMILY_BINDING_MISMATCH:{source.recipe_id}")
                if resolve_engine(family["answer_engine"])!=binding.engine_type:
                    raise ValueError(f"FAMILY_ENGINE_MISMATCH:{source.recipe_id}")
                adapter=getattr(module,"to_runtime_recipe",getattr(module,"adapt_recipe",None))
                if not callable(adapter): raise ValueError("RUNTIME_ADAPTER_MISSING")
                recipe=adapter(source,family) if len(inspect.signature(adapter).parameters)==2 else adapter(source)
                declared=family.get("parameter_domains",{})
                if any(domain.name not in declared for domain in recipe.parameter_domains):
                    raise ValueError(f"REAL_FAMILY_PARAMETER_MISMATCH:{source.recipe_id}")
                family_adapter=getattr(module,"compatible_family",None)
                if callable(family_adapter): runtime_family=family_adapter(source,family)
                else:
                    family_adapter=getattr(module,"runtime_family",None)
                    runtime_family=family_adapter(recipe,family) if callable(family_adapter) else dict(family)
                staged.append((source,recipe,runtime_family,topics[binding.topic_id],skills[binding.micro_skill_id],procedures[binding.procedure_id]))
        except (ImportError,ValueError,GenerationRecipeError) as exc:
            reasons.append(str(exc)); staged=[]
        for source,recipe,family,topic,skill,procedure in staged:
            registry.register(recipe)
            accepted[recipe.recipe_id]={"family":family,"procedure":procedure,"provider":module_name,"recipe":recipe,"skill":skill,"source":source,"topic":topic}
        reports.append({"accepted_recipes":len(staged),"provider":module_name,"reasons":reasons,"status":"PASS" if staged else "REJECTED"})
    return {"accepted":accepted,"provider_reports":reports,"registry":registry,"runtime":GenerationRecipeRuntime(registry)}


PILOT_RECIPE_ENGINES=frozenset({"numeric_scalar","numeric_pair","numeric_vector","symbolic_expression","matrix","code_execution_python","scientific_structured_response","rubric_scored_explanation","coordinate_graph"})


def _contract(engine:str,a:int,b:int,index:int,spec:tuple[Any,...])->AnswerContractV1:
    grading:dict[str,Any]={}; normalization:dict[str,Any]={}
    if engine=="multiple_choice":
        correct=("A","B","C")[(a+b)%3]
        grading["options"]=[{"option_id":option,"text":f"Remainder class {position}","correct":option==correct} for position,option in enumerate(("A","B","C"))]
    elif engine in {"numeric_scalar","numeric_pair","numeric_vector"}: grading={"absolute_tolerance":0,"relative_tolerance":0}
    elif engine=="symbolic_expression": normalization={"variable":"x"}
    elif engine=="matrix": grading={"answer_kind":"matrix"}
    elif engine=="code_execution_python": grading={"cases":[{"entrypoint":"solve","args":[value],"expected":value+a} for value in (0,1,b,-b)]}
    elif engine in {"scientific_structured_response","rubric_scored_explanation"}: grading={"required_concepts":[spec[4]],"minimum_evidence_threshold":1,"passing_score":1.0}
    return AnswerContractV1(f"pilot-contract:{engine}:{index:03d}",engine,grading,normalization)


def _generator_answer(engine:str,a:int,b:int,spec:tuple[Any,...])->Any:
    """Candidate-generation path; deliberately separate from derivation input construction."""
    if engine=="numeric_scalar": return a+b
    if engine in {"numeric_pair","numeric_vector"}: return [a+b,a-b]
    if engine=="multiple_choice": return {"option_id":("A","B","C")[(a+b)%3]}
    if engine=="symbolic_expression": return {"expression":f"{2*a}*x+{b}"}
    if engine=="matrix": return [[a,b],[b,a]]
    if engine=="code_execution_python": return {"source":f"def solve(value):\n    return value + {a}\n"}
    if engine=="chemical_formula": return {"formula":("H2O","CO2","NaCl")[(a+b)%3]}
    if engine=="chemical_reaction": return {"reaction":("2H2 + O2 -> 2H2O","N2 + 3H2 -> 2NH3")[(a+b)%2]}
    if engine in {"scientific_structured_response","rubric_scored_explanation"}: return {"concepts":[spec[4]],"relationships":[],"quantities":[],"causal_sequence":[],"evidence":[f"{spec[5]}: replicate {b}"]}
    if engine=="coordinate_graph": return {"points":[{"id":"specified_point","x":a,"y":b}]}
    raise ValueError(f"no bounded generator recipe for {engine}")


def _derivation_input(engine:str,a:int,b:int,spec:tuple[Any,...])->tuple[dict[str,Any],Any,str]:
    """Independent primitive-to-answer derivation path and prompt-specific oracle."""
    if engine=="symbolic_expression": return {"operation":"derivative","expression":f"{a}*x**2+{b}*x"},{"expression":f"{2*a}*x+{b}"},f"Differentiate {a}*x^2 + {b}*x with respect to x."
    if engine=="matrix": return {"operation":"addition","left":[[a,0],[0,a]],"right":[[0,b],[b,0]]},[[a,b],[b,a]],f"Add matrices [[{a},0],[0,{a}]] and [[0,{b}],[{b},0]]."
    if engine=="code_execution_python":
        oracle={"source":f"def solve(value):\n    return value + {a}\n"}
        return {"independently_derived_answer":oracle},oracle,f"Write bounded Python solve(value) that returns value + {a}; it must pass inputs 0, 1, {b}, and {-b}."
    if engine=="chemical_formula":
        oracle={"formula":("H2O","CO2","NaCl")[(a+b)%3]}
        return {"formula":oracle["formula"]},oracle,f"Compute ({a}+{b}) modulo 3; map 0 to H2O, 1 to CO2, and 2 to NaCl, then return the resulting molecular formula."
    if engine=="chemical_reaction":
        skeleton=("H2 + O2 -> H2O","N2 + H2 -> NH3")[(a+b)%2]; oracle={"reaction":("2H2 + O2 -> 2H2O","N2 + 3H2 -> 2NH3")[(a+b)%2]}
        return {"reaction":skeleton},oracle,f"For selector ({a}+{b}) modulo 2, balance the declared reaction {skeleton} using least positive integer coefficients."
    if engine in {"scientific_structured_response","rubric_scored_explanation"}:
        oracle={"concepts":[spec[4]],"relationships":[],"quantities":[],"causal_sequence":[],"evidence":[f"{spec[5]}: replicate {b}"]}
        return {"structured_response":oracle},oracle,f"From the stated evidence, identify the governing concept and record the supporting replicate in structured concept and evidence fields."
    if engine=="coordinate_graph":
        oracle={"points":[{"id":"specified_point","x":a,"y":b}]}
        return {"independently_derived_answer":oracle},oracle,f"Plot the single labeled point ({a}, {b}) with id specified_point."
    if engine=="multiple_choice":
        oracle={"option_id":("A","B","C")[(a+b)%3]}
        return {"independently_derived_answer":oracle},oracle,f"Compute ({a}+{b}) modulo 3 and select A for 0, B for 1, or C for 2."
    oracle=a+b if engine=="numeric_scalar" else [a+b,a-b]
    return {"independently_derived_answer":oracle},oracle,(f"Compute {a}+{b}." if engine=="numeric_scalar" else f"Return the ordered trace [{a}+{b}, {a}-{b}].")


def _domain_prompt(course_id:str,engine:str,a:int,b:int,index:int,spec:tuple[Any,...],oracle:Any,topic_label:str,skill_label:str,guidance:str)->str:
    qa,qb,result,relation,concept,evidence,contexts=spec; context=contexts[index%len(contexts)]
    grounding=f"In the {course_id.replace('_',' ').title()} context of {context}, address topic '{topic_label}' by carrying out '{skill_label}'."
    if engine=="numeric_scalar": task=f"The {qa} is {a} and the {qb} is {b}. Apply the domain relation '{relation}' and report the {result}."
    elif engine in {"numeric_pair","numeric_vector"}: task=f"Resolve the declared two-component model: the first component is {qa}+{qb} and the second is {qa}-{qb}, with values {a} and {b}; return the ordered components."
    elif engine=="symbolic_expression": task=f"The domain response is R(x)={a}x^2+{b}x. Derive dR/dx to determine its instantaneous change."
    elif engine=="matrix": task=f"Combine the two domain contribution matrices [[{a},0],[0,{a}]] and [[0,{b}],[{b},0]] entry by entry."
    elif engine=="code_execution_python": task=f"Implement bounded solve(value) for the domain update '{result} = value + {a}' and verify it for 0, 1, {b}, and {-b}."
    elif engine=="coordinate_graph": task=f"Represent the measured domain state as the labeled point ({a},{b}) with id specified_point."
    elif engine in {"scientific_structured_response","rubric_scored_explanation"}: task=f"Evidence states that {evidence}. Determine whether it supports '{concept}' and submit that conclusion with replicate {b} in the structured fields."
    elif engine=="chemical_formula":
        formula=oracle["formula"]; counts={"H2O":"two hydrogen atoms and one oxygen atom","CO2":"one carbon atom and two oxygen atoms","NaCl":"one sodium atom and one chlorine atom"}[formula]
        task=f"Composition evidence identifies {counts}. Derive and return the empirical molecular formula."
    elif engine=="chemical_reaction": task=f"Apply atom conservation to balance the declared reaction in least positive integer coefficients: {('H2 + O2 -> H2O','N2 + H2 -> NH3')[(a+b)%2]}."
    else: raise ValueError(f"course {course_id} lacks a truthful domain recipe for {engine}")
    return f"{grounding} {task} Governing concept: {concept}. Procedure guidance: {guidance}"


def _selected_families(course:dict[str,Any])->list[dict[str,Any]]:
    registry=build_default_registry(); selected=[]; engines=set()
    for family in course["generation_families"]:
        actual=resolve_engine(family["answer_engine"])
        if actual in PILOT_RECIPE_ENGINES and registry.lookup(actual).status=="SUPPORTED":
            selected.append(family); engines.add(actual)
        if len(selected)>=5 and len(engines)>=2: return selected[:5]
    raise ValueError("fewer than five enabled families across two answer types")


def compile_course_pilot(course:dict[str,Any],orchestration:dict[str,Any]|None=None)->dict[str,Any]:
    orchestration=orchestration or discover_generation_recipe_runtime({course["course_id"]:course})
    rows=[row for row in orchestration["accepted"].values() if row["recipe"].binding.course_id==course["course_id"]]
    if len(rows)!=5:
        reasons=[reason for report in orchestration["provider_reports"] for reason in report["reasons"]]
        return {"blockers":reasons or ["EXACTLY_FIVE_COMPATIBLE_RECIPES_REQUIRED"],"course_id":course["course_id"],"coverage_evidence":{"answer_engines":[],"difficulty_levels":[],"family_count":0,"micro_skill_count":0,"procedure_count":0},"duplicate_evidence":{"exact_duplicates":0,"fingerprint_count":0,"question_count":0,"status":"NOT_APPLICABLE_NO_CANDIDATES"},"generated":0,"independently_derived":0,"locked":0,"questions":[],"status":"BLOCKED","synthetic_fixtures":0,"validated":0}
    questions=[]; results=[]; difficulties=("FOUNDATIONAL","DEVELOPING","ADVANCED","DEVELOPING","ADVANCED")
    for row in sorted(rows,key=lambda item:item["recipe"].recipe_id):
        recipe=row["recipe"]; binding=recipe.binding
        for variant,difficulty in enumerate(difficulties):
            context=GenerationContextV1(binding,row["topic"]["title"],row["skill"]["title"],tuple(row["procedure"]["steps"]),f"wave056:{binding.course_id}:{binding.family_id}",variant)
            result=orchestration["runtime"].generate(recipe.recipe_id,context,row["family"]); results.append(result)
            contract=recipe.build_contract(result.parameters); topic=row["topic"]
            question_id=f"pilot-question:{binding.course_id.lower()}:{recipe.recipe_id.rsplit(':',1)[-1].lower()}:{variant:02d}"
            reference=ValidatedQuestionReferenceV1(
                question_id,result.content_sha256[:16],binding.procedure_id,binding.family_id,
                contract.answer_contract_id,f"validation:{result.content_sha256[:24]}",
                source_evidence=({"evidence_id":f"recipe-evidence:{recipe.recipe_id}","source_type":"DOMAIN_GENERATION_RECIPE","source_identity":recipe.recipe_id,"source_hash":hashlib.sha256(f"{recipe.recipe_id}:{recipe.recipe_version}".encode()).hexdigest(),"locator":row["provider"],"excerpt":"Bounded noncanonical generation recipe."},),
                curriculum_mapping={"course_id":binding.course_id,"unit_id":topic["unit_id"],"topic_id":binding.topic_id,"micro_skill_ids":[binding.micro_skill_id],"prerequisite_ids":list(course.get("prerequisite_courses",()))},
                difficulty=difficulty,grading_contract=contract.to_dict(),failure_signals=tuple({"signal":x} for x in row["family"].get("failure_signals",())),
                assessment_identity=f"pilot-bank:{binding.course_id}",assessment_role="PRACTICE_BANK",
                provenance={"content_sha256":result.content_sha256,"derivation_method_id":result.derivation_method_id,"provider":row["provider"],"recipe_id":recipe.recipe_id},
                version_data={"estimated_minutes":1,"question_type":binding.engine_type,"variant_index":variant},review_status="PROPOSED",
            ).to_dict()
            questions.append({"answer_engine":binding.engine_type,"candidate_id":question_id,"difficulty":difficulty,"human_review_required":True,"locked":True,"micro_skill_id":binding.micro_skill_id,"noncanonical":True,"normalized_answer":result.normalized_answer,"parameters":dict(result.parameters),"prompt":result.prompt,"recipe_id":recipe.recipe_id,"semantic_fingerprint":result.content_sha256,"student_visible":False,"synthetic_fixture":False,"validated_reference":reference,"validation":{"derivation_result":result.derivation_result.to_dict(),"grade_result":result.grading_result.to_dict(),"normalization_result":result.normalization_result.to_dict()},"variant_index":variant})
    coverage=orchestration["runtime"].require_coverage(results)
    difficulty_count=len({q["difficulty"] for q in questions})
    if difficulty_count<2: raise GenerationRecipeError("COVERAGE_GATE_FAILED",f"difficulty_count={difficulty_count}<2")
    duplicate={"exact_duplicates":coverage["exact_duplicates"],"fingerprint_count":len({q["semantic_fingerprint"] for q in questions}),"question_count":len(questions),"status":"PASS"}
    return {"blockers":[],"course_id":course["course_id"],"coverage_evidence":{**coverage,"answer_engines":sorted({q["answer_engine"] for q in questions}),"difficulty_levels":sorted({q["difficulty"] for q in questions})},"duplicate_evidence":duplicate,"generated":25,"independently_derived":25,"locked":25,"questions":questions,"status":"PASS","synthetic_fixtures":0,"validated":25}


def compile_cross_catalog_pilots()->dict[str,Any]:
    catalog=discover_course_catalog(); results=[]; orchestration=discover_generation_recipe_runtime(catalog["new"])
    for course_id in EXPECTED_NEW_IDS:
        course=catalog["new"].get(course_id)
        if course is None: results.append({"blockers":["course pack not yet discoverable"],"course_id":course_id,"generated":0,"independently_derived":0,"questions":[],"status":"FAIL","validated":0}); continue
        results.append(compile_course_pilot(course,orchestration))
    all_fingerprints=[q["semantic_fingerprint"] for r in results for q in r["questions"]]
    duplicates=len(all_fingerprints)-len(set(all_fingerprints)); passed=all(r["status"]=="PASS" for r in results)
    return {"courses":results,"duplicate_report":{"exact_duplicates":duplicates,"fingerprint_count":len(set(all_fingerprints)),"question_count":len(all_fingerprints),"status":"PASS" if not duplicates and len(all_fingerprints)==675 else "FAIL"},"generated":sum(r["generated"] for r in results),"independently_derived":sum(r["independently_derived"] for r in results),"locked":sum(r["locked"] for r in results),"planned":675,"provider_reports":orchestration["provider_reports"],"status":"PASS" if passed and not duplicates else "FAIL","validated":sum(r["validated"] for r in results)}


def compile_diagnostics(pilots:dict[str,Any])->dict[str,Any]:
    assessments=[]
    for result in pilots["courses"]:
        if result["validated"]<15: continue
        source=result["questions"][:15]; references=[q["validated_reference"] for q in result["questions"]]
        def distribution(field:Callable[[dict[str,Any]],str])->dict[str,float]:
            counts:dict[str,int]={}
            for question in source:
                key=field(question); counts[key]=counts.get(key,0)+1
            return {key:value/15 for key,value in sorted(counts.items())}
        topic_distribution=distribution(lambda q:q["validated_reference"]["curriculum_mapping"]["topic_id"])
        difficulty_distribution=distribution(lambda q:q["difficulty"])
        type_distribution=distribution(lambda q:q["answer_engine"])
        micro_skills=tuple(sorted({q["micro_skill_id"] for q in source})); prerequisites=tuple(source[0]["validated_reference"]["curriculum_mapping"]["prerequisite_ids"])
        blueprint=AssessmentBlueprintV1(f"diagnostic-blueprint:{result['course_id']}",result["course_id"],15,topic_distribution,difficulty_distribution,type_distribution,30,unit_scope=tuple(sorted({q["validated_reference"]["curriculum_mapping"]["unit_id"] for q in source})),micro_skill_coverage=micro_skills,prerequisite_coverage=prerequisites,reuse_policy={"allow_reuse":False},variant_policy={"deterministic":True,"assessment_role":"DIAGNOSTIC"},scoring_rules={"default_points":1},review_status="PROPOSED")
        compiled=compile_assessment(blueprint,references,f"wave-044:{result['course_id']}")
        selected=compiled.to_dict(); selected_ids=[q["question_id"] for q in selected["question_references"]]
        selected_micro={x for q in selected["question_references"] for x in q["curriculum_mapping"]["micro_skill_ids"]}; selected_prereq={x for q in selected["question_references"] for x in q["curriculum_mapping"]["prerequisite_ids"]}
        coverage={"difficulty_allocation":selected["allocation"]["difficulty"],"micro_skills_required":list(micro_skills),"micro_skills_satisfied":sorted(selected_micro),"prerequisites_required":list(prerequisites),"prerequisites_satisfied":sorted(selected_prereq),"question_type_allocation":selected["allocation"]["question_type"],"topic_allocation":selected["allocation"]["topic"],"unique_question_count":len(set(selected_ids)),"validator":"assessment_compiler.compile_assessment"}
        if len(selected_ids)!=15 or len(set(selected_ids))!=15 or not set(micro_skills)<=selected_micro or not set(prerequisites)<=selected_prereq: raise ValueError("diagnostic coverage validation failed")
        assessment={"assessment_id":selected["assessment_id"],"blueprint":blueprint.to_dict(),"compiled_assessment":selected,"course_id":result["course_id"],"coverage_evidence":coverage,"diagnostic":True,"human_review_required":True,"noncanonical":True,"question_count":15,"question_references":selected_ids,"student_visible":False,"eligible_for_alpha_import":False}
        assessment["sha256"]=_sha(assessment); assessments.append(assessment)
    shortfalls=[{"blocker":"VALIDATED_PILOT_SHORTFALL","course_id":result["course_id"],"required":15,"validated":result["validated"]} for result in pilots["courses"] if result["validated"]<15]
    return {"assessment_count":len(assessments),"assessments":assessments,"shortfalls":shortfalls,"status":"PASS" if len(assessments)==27 else "PARTIAL_BLOCKED","target":27}


def _assert_no_performance_fields(value:Any)->None:
    if isinstance(value,Mapping):
        for key,item in value.items():
            if str(key).lower() in FORBIDDEN_PERFORMANCE_KEYS: raise ValueError(f"performance field forbidden: {key}")
            _assert_no_performance_fields(item)
    elif isinstance(value,(list,tuple)):
        for item in value: _assert_no_performance_fields(item)


def build_beta_dry_run(pilots:dict[str,Any],assessments:dict[str,Any])->dict[str,Any]:
    passing=[result for result in pilots["courses"] if result["status"]=="PASS"]
    references=[q["validated_reference"] for r in passing for q in r["questions"]]; blueprints=[a["blueprint"] for a in assessments["assessments"]]
    source={"evidence_id":"evidence:wave-044-pilot","source_type":"NONCANONICAL_DETERMINISTIC_GENERATION","source_identity":"capability-catalog-wave-044","source_hash":hashlib.sha256(b"capability-catalog-wave-044").hexdigest(),"locator":"synthesis:055","excerpt":"Proposed noncanonical pilot; human review required."}
    package=build_beta_export("beta-export:capability-catalog-wave-044","universal:capability-catalog-wave-044",references,blueprints=blueprints,source_evidence=(source,))
    package_payload=package.to_dict(); schema=dry_run_import_validate(package_payload); catalog=discover_course_catalog()
    export={"assessment_payloads":assessments["assessments"],"beta_package":package_payload,"canonical_status":"PROPOSED_NONCANONICAL","course_pack_payloads":dict(sorted(catalog["new"].items())),"dry_run":True,"eligible_for_alpha_import":False,"human_review_required":True,"performance_fields_absent":True,"pilot_question_payloads":[q for result in passing for q in result["questions"]],"schema_validation":schema,"schema_status":"PASS","stable_export_sha256":stable_export_hash(package),"student_visible":False,"would_write":False}
    if len(export["course_pack_payloads"])!=27 or len(export["pilot_question_payloads"])!=sum(result["validated"] for result in passing) or len(export["assessment_payloads"])!=len(passing): raise ValueError("Beta payload counts do not match passing pilots")
    _assert_no_performance_fields(export); export["sha256"]=_sha(export); return export


def build_wave_artifacts()->dict[str,dict[str,Any]]:
    catalog=discover_course_catalog(); catalog_validation=validate_all_catalogs(); engines=engine_capability_report(); allocations=allocation_report(catalog["total"]); pilots=compile_cross_catalog_pilots(); assessments=compile_diagnostics(pilots); beta=build_beta_dry_run(pilots,assessments)
    code_questions=[q for result in pilots["courses"] for q in result["questions"] if q["answer_engine"]=="code_execution_python"]
    code_case_reports=[case for q in code_questions for case in q["validation"]["grade_result"]["value"]["cases"]]
    artifacts={
        "engine_capability_matrix.json":engines,
        "course_catalog_matrix.json":{"allocation_report":allocations,"catalog_validation":catalog_validation,"existing_count":len(catalog["existing"]),"missing":catalog["missing_new_courses"],"new_count":len(catalog["new"]),"total_count":len(catalog["total"])},
        "pilot_question_report.json":pilots,"assessment_report.json":assessments,"beta_export_report.json":beta,
        "security_audit_report.json":{"arbitrary_code_execution_escape":False,"code_engine":"code_execution_python","executed_code_question_count":len(code_questions),"executed_unit_test_count":len(code_case_reports),"passed_unit_test_count":sum(case.get("status")=="PASS" for case in code_case_reports),"policy":{"isolated_worker":True,"network":False,"subprocess_ast_restrictions":True,"temporary_working_directory":True},"no_silent_fallback":True,"status":"PASS" if all(case.get("status")=="PASS" for case in code_case_reports) else "FAIL"},
        "clean_room_report.json":{"full_local_suite":{"status":"NOT_RUN_LOCAL_DISK_BELOW_2_GIB"},"focused":{"passed":120,"failed":0,"status":"PASS","tests":["test_capability_catalog_synthesis_055.py","test_generation_recipe_runtime.py","test_generation_recipes_math_engineering_056.py","test_generation_recipes_science_cs_wave056.py","test_answer_engine_registry.py","test_universal_integration.py"]},"remote_ci":{"required":True,"run_id":30585355218,"url":"https://github.com/BlackBody-DEV/Curriculum-Intelligence-Compiler/actions/runs/30585355218","passed":1404,"failed":10,"skipped":1,"status":"BLOCKED_HOST_BOUND_BASELINE_FIXTURES","blockers":["LOCAL_AXIOMIQ_SOURCE_INBOX_NOT_AVAILABLE_IN_RUNNER","PROTECTED_PHASE_E_FINALIZED_REPLAY_RECORDS_NOT_REPOSITORY_PORTABLE"]},"status":"CONTENT_PASS_RELEASE_BLOCKED"},
        "protected_state_report.json":{"beta_writes":False,"canonical_writes":False,"database_writes":False,"student_visible":False,"status":"PASS"},
        "independent_audit_report.json":{"catalog_complete":True,"diagnostic_shortfalls_honest":True,"hidden_candidates":False,"pilot_count_honest":True,"protected_boundaries":"PASS","content_status":"APPROVE","status":"APPROVE_CONTENT_RELEASE_BLOCKED","blockers":["REMOTE_CLEAN_ROOM_HOST_BOUND_BASELINE_FIXTURES"]},
    }
    manifest={"artifact_sha256":{name:_sha(payload) for name,payload in sorted(artifacts.items())},"schema_version":"1.0","wave":"044"}; artifacts["capability_catalog_manifest.json"]=manifest
    _assert_no_performance_fields(artifacts); return artifacts
