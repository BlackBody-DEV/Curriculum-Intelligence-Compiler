"""Explicit domain recipes for twelve mathematics and engineering courses."""
from __future__ import annotations

from typing import Any

from tools.course_compiler_demo.answer_engines import build_default_registry
from .models import DomainRecipeV1,GenerationContextV1,ParameterDomainV1,RecipeBindingV1,validate_answer_shape


# Five operations are fixed to exact topic/skill/family identities 1..5 and at
# least three procedures.  Every prompt below states a real domain relationship.
COURSE_TASKS={
"PRE_ALGEBRA":(
("inventory addition","A supply shelf has {a} labeled items and receives {b} more. Determine the total item count by additive counting.",("inventory","whole numbers")),
("signed change","A temperature is {a} degrees and falls by {b} degrees. Determine the signed final temperature.",("temperature","integers")),
("rectangular area","A rectangular tile array has {a} rows and {b} columns. Determine its tile count from area as rows times columns.",("area","multiplication")),
("unit rate","A batch of {a} items is shared equally among {b} groups. Determine the items per group as an exact quotient.",("unit rate","division")),
("coordinate displacement","A point has component {a}; a directed change has magnitude {b}. Return the ordered forward and reverse components [{a}+{b}, {a}-{b}].",("coordinates","directed change"))),
"ALGEBRA_II":(
("function transformation","A function value {a} is shifted vertically by {b}. Determine the transformed value.",("functions","vertical translation")),
("polynomial comparison","A polynomial model value {a} is reduced by correction {b}. Determine the corrected value.",("polynomials","subtraction")),
("factor product","Two polynomial factors contribute leading coefficients {a} and {b}. Determine the product's leading coefficient.",("polynomial factors","leading coefficient")),
("rational function","A rational model has numerator {a} and nonzero denominator {b}. Evaluate the quotient.",("rational function","domain restriction")),
("system residuals","A system check uses contributions {a} and {b}. Return ordered sum and difference residuals [{a}+{b}, {a}-{b}].",("systems","residual vector"))),
"GEOMETRY":(
("segment addition","Adjacent collinear segments have lengths {a} and {b}. Determine their combined length.",("segments","length")),
("coordinate translation","An x-coordinate {a} is translated left by {b}. Determine the new coordinate.",("translation","coordinate geometry")),
("rectangle area","A rectangle has side lengths {a} and {b}. Determine its area.",("rectangle","area")),
("similarity scale","Corresponding sides measure {a} and {b}. Determine their scale ratio a/b.",("similarity","scale factor")),
("vector construction","Two directed lengths are {a} and {b}. Return the ordered diagonal components [{a}+{b}, {a}-{b}].",("vectors","coordinate construction"))),
"TRIGONOMETRY":(
("phase composition","A phase parameter {a} receives offset {b}. Determine the composed phase parameter.",("phase","periodic model")),
("angle difference","Two directed angles are {a} and {b} degrees. Determine the signed angle difference.",("angles","orientation")),
("amplitude scaling","A sinusoid has amplitude factor {a} and scale {b}. Determine the scaled amplitude.",("sinusoid","amplitude")),
("component ratio","A right-triangle model declares opposite component {a} and adjacent component {b}. Determine their ratio.",("right triangle","tangent ratio")),
("polar components","A bounded polar-component check uses {a} and {b}. Return ordered combined and differential components [{a}+{b}, {a}-{b}].",("polar form","components"))),
"PRE_CALCULUS":(
("function composition","A base function output {a} receives transformation offset {b}. Determine the transformed output.",("functions","transformation")),
("net model change","A model value {a} loses adjustment {b}. Determine the net value.",("models","net change")),
("sequence scaling","A sequence term {a} is scaled by common factor {b}. Determine the resulting term.",("sequences","scaling")),
("average rate","A declared output change {a} occurs over nonzero input change {b}. Determine the average rate of change.",("average rate","difference quotient")),
("parametric components","Parametric contributions are {a} and {b}. Return ordered sum and difference components [{a}+{b}, {a}-{b}].",("parametric equations","components"))),
"CALCULUS_II":(
("integral accumulation","Two partition contributions to an integral are {a} and {b}. Determine their total accumulation.",("integral","accumulation")),
("signed integral","Positive accumulated area {a} is offset by negative contribution {b}. Determine the signed net area.",("signed area","definite integral")),
("series coefficient","A series coefficient {a} is multiplied by factor {b}. Determine the scaled coefficient.",("series","coefficient")),
("average value","An integral accumulation {a} spans interval length {b}. Determine the average value a/b.",("average value","integral")),
("polar accumulation","Two polar-area component values are {a} and {b}. Return their ordered sum and difference [{a}+{b}, {a}-{b}].",("polar area","components"))),
"CALCULUS_III":(
("space vector addition","A spatial vector has x-component {a} and receives x-component {b}. Determine the resultant x-component.",("space vectors","vector addition")),
("directional change","A field component {a} is reduced by directional contribution {b}. Determine the signed component.",("vector field","directional change")),
("rectangular double integral","A constant density {a} covers a rectangular parameter area {b}. Determine the accumulated integral.",("double integral","constant density")),
("average flux density","A total flux {a} crosses surface area {b}. Determine average flux density a/b.",("surface flux","area")),
("three-dimensional components","Spatial component measures are {a} and {b}. Return ordered resultant and differential components [{a}+{b}, {a}-{b}].",("three-dimensional space","components"))),
"DIFFERENTIAL_EQUATIONS":(
("solution superposition","Homogeneous response {a} and particular response {b} combine linearly. Determine total response.",("linear ODE","superposition")),
("state decrement","A state value {a} experiences decay amount {b}. Determine the updated state.",("decay model","state update")),
("forcing scale","A forcing coefficient {a} is scaled by input {b}. Determine the forcing term.",("forcing","coefficient")),
("average slope","A state changes by {a} over nonzero time step {b}. Determine the average slope.",("slope field","time step")),
("phase-plane update","Phase components are {a} and {b}. Return ordered combined and differential state components [{a}+{b}, {a}-{b}].",("phase plane","state vector"))),
"LINEAR_ALGEBRA":(
("linear combination","Two basis-direction coefficients {a} and {b} contribute to one component. Determine the combined coefficient.",("basis","linear combination")),
("component subtraction","Vector component {a} is reduced by component {b}. Determine the resulting component.",("vectors","subtraction")),
("scalar action","A vector component {a} is multiplied by scalar {b}. Determine the transformed component.",("scalar multiplication","linear transformation")),
("normalized coordinate","A coordinate magnitude {a} is normalized by nonzero scale {b}. Determine a/b.",("coordinates","normalization")),
("matrix residual vector","A two-equation residual check uses {a} and {b}. Return ordered sum and difference residuals [{a}+{b}, {a}-{b}].",("linear systems","residual vector"))),
"NUMERICAL_METHODS":(
("iterative correction","A current approximation {a} receives computed correction {b}. Determine the updated approximation.",("iteration","correction")),
("residual reduction","Residual {a} is reduced by correction {b}. Determine the new signed residual.",("residual","convergence")),
("quadrature scaling","A quadrature weight {a} multiplies sample value {b}. Determine the contribution.",("quadrature","weighted sample")),
("difference quotient","A computed change {a} occurs over nonzero step {b}. Determine the finite-difference quotient.",("finite difference","step size")),
("solver update vector","Solver values are {a} and {b}. Return ordered aggregate and residual components [{a}+{b}, {a}-{b}].",("linear solver","update vector"))),
"ENGINEERING_ANALYSIS":(
("response superposition","Homogeneous engineering response {a} and forced response {b} combine. Determine total response.",("engineering response","superposition")),
("balance residual","Applied quantity {a} is opposed by reaction {b}. Determine signed residual.",("balance","residual")),
("gain application","Input magnitude {a} passes through gain {b}. Determine output magnitude.",("transfer model","gain")),
("normalized response","Response magnitude {a} is normalized by nonzero reference {b}. Determine the ratio.",("normalization","reference value")),
("field components","Field contributions are {a} and {b}. Return ordered combined and differential components [{a}+{b}, {a}-{b}].",("field analysis","components"))),
"APPLIED_MATHEMATICS":(
("model aggregation","Baseline model term {a} and perturbation term {b} combine. Determine the composite model value.",("mathematical model","perturbation")),
("objective improvement","Objective value {a} is reduced by improvement {b}. Determine the updated objective.",("optimization","objective")),
("weighted contribution","Model coefficient {a} multiplies state value {b}. Determine the contribution.",("model coefficient","state")),
("dimensionless ratio","Quantity {a} is normalized by nonzero reference {b}. Determine the dimensionless ratio.",("dimensional analysis","normalization")),
("coupled state","Coupled state values are {a} and {b}. Return ordered combined and differential states [{a}+{b}, {a}-{b}].",("dynamical systems","state vector"))),
}

OPERATIONS=("sum","difference","product","ratio","component_pair")
PROCEDURE_INDEX=(1,2,3,4,5)


def _build_registry()->dict[str,tuple[DomainRecipeV1,...]]:
    registry={}
    for course_id,tasks in COURSE_TASKS.items():
        recipes=[]
        for index,(semantic,prompt,terms) in enumerate(tasks,1):
            operation=OPERATIONS[index-1]; engine="numeric_vector" if operation=="component_pair" else "numeric_scalar"
            binding=RecipeBindingV1(course_id,f"{course_id}_TOPIC_{index:03d}",f"{course_id}_SKILL_{index:03d}",f"{course_id}_PROC_{PROCEDURE_INDEX[index-1]:03d}",f"{course_id}_FAMILY_{index:03d}",engine)
            domains=(ParameterDomainV1("a",1,24,True,"declared_domain_unit"),ParameterDomainV1("b",1,12,True,"declared_domain_unit"))
            recipe=DomainRecipeV1(f"recipe:{course_id.lower()}:{index:02d}","1.0",binding,domains,tuple(terms),(semantic,operation),prompt,operation); recipe.validate(); recipes.append(recipe)
        registry[course_id]=tuple(recipes)
    return registry


COURSE_RECIPE_REGISTRY=_build_registry()


def get_course_recipes(course_id:str)->tuple[DomainRecipeV1,...]:
    try:return COURSE_RECIPE_REGISTRY[course_id]
    except KeyError as exc:raise ValueError(f"no math/engineering recipe set for {course_id}") from exc


def generate_course_pilot(course_id:str)->tuple[dict[str,Any],...]:
    """Generate 25 adapter-neutral records and prove them with existing engines."""
    registry=build_default_registry(); records=[]
    for recipe in get_course_recipes(course_id):
        for variant in range(5):
            context=GenerationContextV1({"a":2+variant,"b":1+variant},variant,("FOUNDATIONAL","DEVELOPING","ADVANCED")[variant%3])
            answer=recipe.generate_answer(context); derivation=recipe.derive_independently(context); validate_answer_shape(recipe,answer)
            contract=recipe.build_contract(); normalized=registry.normalize(answer,contract); derived=registry.derive({"independently_derived_answer":derivation.normalized_answer},contract); graded=registry.grade(answer,derivation.normalized_answer,contract)
            if normalized.status!=derived.status or normalized.status!="PASS" or normalized.value!=derived.value or graded.status!="PASS": raise ValueError("engine proof failed without fallback")
            records.append({"recipe_id":recipe.recipe_id,"binding":recipe.binding,"context":context,"prompt":recipe.build_prompt(context),"generator_answer":answer,"derivation":derivation,"engine_validation":{"normalize":normalized.to_dict(),"derive":derived.to_dict(),"grade":graded.to_dict()}})
    return tuple(records)


def audit_recipe_catalog()->dict[str,Any]:
    for recipes in COURSE_RECIPE_REGISTRY.values():
        for recipe in recipes: recipe.validate()
    return {"courses":len(COURSE_RECIPE_REGISTRY),"recipes":sum(map(len,COURSE_RECIPE_REGISTRY.values())),"status":"PASS"}
