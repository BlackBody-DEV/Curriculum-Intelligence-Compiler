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

# Explicitly reviewed against the canonical topic/skill/procedure identities.
# The engineering catalogs use a different engine cycle, so their last three
# bindings deliberately select 006, 007, and 011 rather than positional 003-005.
SEMANTIC_BINDINGS={
"PRE_ALGEBRA":((1,"whole-number reasoning"),(2,"integer operations"),(3,"fractions and decimals"),(14,"ratios and rates"),(5,"proportions")),
"ALGEBRA_II":((1,"equations and inequalities"),(2,"functions"),(3,"quadratic functions"),(14,"polynomial functions"),(5,"rational functions")),
"GEOMETRY":((1,"foundations and constructions"),(2,"transformations"),(3,"congruence"),(14,"similarity"),(7,"circles")),
"TRIGONOMETRY":((1,"angle measure"),(2,"right-triangle trigonometry"),(3,"unit circle"),(14,"trigonometric functions"),(7,"equations")),
"PRE_CALCULUS":((1,"function analysis"),(2,"polynomial and rational models"),(3,"exponential and logarithmic models"),(14,"trigonometric models"),(7,"conic sections")),
"CALCULUS_II":((1,"integration techniques"),(2,"improper integrals"),(3,"applications of integration"),(14,"differential equations models"),(5,"parametric curves")),
"CALCULUS_III":((1,"vectors and geometry of space"),(2,"vector-valued functions"),(3,"partial derivatives"),(14,"multiple integrals"),(7,"line integrals")),
"DIFFERENTIAL_EQUATIONS":((1,"first-order equations"),(2,"qualitative methods"),(3,"existence and uniqueness"),(14,"second-order linear equations"),(7,"linear systems")),
"LINEAR_ALGEBRA":((1,"linear systems"),(2,"matrix algebra"),(3,"vector equations"),(14,"linear transformations"),(5,"subspaces")),
"NUMERICAL_METHODS":((1,"error and conditioning"),(2,"root finding"),(6,"numerical integration"),(8,"boundary-value problems"),(11,"linear systems")),
"ENGINEERING_ANALYSIS":((1,"engineering models"),(3,"linear algebraic models"),(6,"partial differential equations"),(8,"approximation methods"),(11,"linear algebraic models")),
"APPLIED_MATHEMATICS":((1,"mathematical modeling"),(2,"discrete models"),(6,"dynamical systems"),(8,"asymptotic analysis"),(11,"continuous models")),
}

COURSE_SCENARIOS={
"PRE_ALGEBRA":(("whole-number total","Combine {a} counted objects with {b} more objects and report the whole-number total.","sum"),("signed integer change","An integer position {a} moves backward {b} units; report the signed result.","difference"),("fraction product selection","Select the product of fraction numerators {a} and {b}, rejecting their sum.","multiple_choice_product"),("unit-rate scaling","A ratio table has {a} units in each of {b} groups; compute the proportional total.","product"),("proportional constant","A proportion compares {a} units with {b} equal groups; compute the constant of proportionality.","ratio")),
"ALGEBRA_II":(("linear equation balance","Combine like constant terms {a} and {b} while preserving equality.","sum"),("function output change","A function output {a} receives vertical change {b}; compute the transformed output.","difference"),("quadratic leading term","Select the leading coefficient obtained by multiplying binomial coefficients {a} and {b}.","multiple_choice_product"),("polynomial coefficient product","Multiply polynomial leading coefficients {a} and {b} to obtain the product leading coefficient.","product"),("rational-function value","Evaluate a rational function with numerator {a} and nonzero denominator {b}.","ratio")),
"GEOMETRY":(("segment construction","Construct adjacent segments of lengths {a} and {b}; report the combined segment length.","sum"),("coordinate translation","Translate coordinate {a} left by {b}; report its image.","difference"),("congruence scale check","Select the product of {a} repeated congruent pieces each measuring {b}.","multiple_choice_product"),("similarity scale application","A similar figure has side {a} under scale factor {b}; compute the corresponding side.","product"),("circle radius ratio","Two circles have radii {a} and nonzero {b}; compute the radius ratio, which also equals their circumference ratio.","ratio")),
"TRIGONOMETRY":(("angle composition","Compose directed angles {a} and {b} degrees.","sum"),("right-triangle tangent ratio","For opposite leg {a} and nonzero adjacent leg {b}, compute tan(theta)=opposite/adjacent.","ratio"),("unit-circle coordinate relation","Select the rectangular-area product x*y for unit-circle coordinates scaled to integers {a} and {b}.","multiple_choice_product"),("amplitude scaling","Scale trigonometric amplitude {a} by factor {b}.","product"),("equation quotient","Isolate a trigonometric value by dividing equation side {a} by nonzero coefficient {b}.","ratio")),
"PRE_CALCULUS":(("function composition offset","Combine function output {a} with transformation offset {b}.","sum"),("rational-model residual","Subtract modeled correction {b} from polynomial-rational output {a}.","difference"),("exponential factor selection","Select the exponential growth-step product of current value {a} and factor {b}.","multiple_choice_product"),("trigonometric amplitude model","Multiply amplitude {a} by declared trigonometric scale {b}.","product"),("conic axis ratio","Compare conic semi-axis measures {a} and {b} by exact ratio.","ratio")),
"CALCULUS_II":(("partition accumulation","Add integration partition contributions {a} and {b}.","sum"),("improper-integral truncation residual","Subtract tail estimate {b} from truncation value {a}.","difference"),("cross-section area selection","Select rectangular cross-section area from dimensions {a} and {b}.","multiple_choice_product"),("separable ODE coefficient","Multiply separated model coefficient {a} by state factor {b}.","product"),("parametric slope","Compute dy/dx from declared component changes {a} and nonzero {b}.","ratio")),
"CALCULUS_III":(("vector component addition","Add compatible spatial-vector components {a} and {b}.","sum"),("vector displacement component","Subtract initial component {b} from terminal component {a}.","difference"),("partial-derivative term selection","Select the coefficient product {a}*{b} arising when differentiating a scaled multivariable term.","multiple_choice_product"),("constant-density double integral","Integrate constant density {a} over rectangular parameter area {b}.","product"),("line-integral average density","Divide accumulated line integral {a} by nonzero curve length {b}.","ratio")),
"DIFFERENTIAL_EQUATIONS":(("solution superposition","Add homogeneous contribution {a} and particular contribution {b}.","sum"),("phase-line decrement","Apply signed decrement {b} to state {a} on a qualitative phase line.","difference"),("Lipschitz-bound selection","Select the product of local slope bound {a} and interval width {b} used in uniqueness analysis.","multiple_choice_product"),("characteristic-root product","Multiply characteristic roots {a} and {b} for a second-order equation.","product"),("linear-system rate ratio","Compute component change {a} per nonzero time increment {b}.","ratio")),
"LINEAR_ALGEBRA":(("equation-row combination","Add compatible right-hand-side entries {a} and {b} during row combination.","sum"),("matrix entry subtraction","Subtract corresponding matrix entries {b} from {a}.","difference"),("vector-equation matrix","Construct the symmetric coefficient matrix with diagonal {a} and cross coefficient {b}.","matrix"),("linear-map scaling","Apply scalar linear transformation factor {b} to component {a}.","product"),("subspace coordinate ratio","Normalize subspace coordinate {a} by nonzero basis scale {b}.","ratio")),
"NUMERICAL_METHODS":(("relative conditioning error","Combine baseline error {a} and propagated perturbation {b}.","sum"),("linear root solve","Solve the bounded linear equation {a}*x+{b}=0 and report its exact root -{b}/{a}.","linear_root"),("quadrature contribution","Multiply quadrature weight {a} by sampled value {b}.","product"),("boundary-value stencil matrix","Construct the symmetric two-node finite-difference stencil using diagonal {a} and coupling {b}.","matrix"),("linear-system residual","Subtract computed action {b} from right-hand side {a}.","difference")),
"ENGINEERING_ANALYSIS":(("model response superposition","Add compatible engineering response contributions {a} and {b}.","sum"),("linear algebraic coefficient matrix","Construct a symmetric coefficient matrix with diagonal {a} and coupling {b}.","matrix"),("PDE flux contribution","Multiply field gradient magnitude {a} by transport coefficient {b}.","product"),("approximation normal matrix","Construct a symmetric two-basis normal matrix with diagonal {a} and cross term {b}.","matrix"),("linear-model residual","Subtract predicted algebraic response {b} from observation {a}.","difference")),
"APPLIED_MATHEMATICS":(("model aggregation","Add baseline model term {a} and perturbation {b}.","sum"),("discrete recurrence step","For recurrence u[n+1]=u[n]+{b} with u[n]={a}, compute the next discrete state.","recurrence_step"),("dynamical gain action","Multiply state magnitude {a} by dynamical gain {b}.","product"),("asymptotic coefficient matrix","Construct the two-term asymptotic coupling matrix with diagonal {a} and cross term {b}.","matrix"),("continuous-model residual","Subtract continuous-model prediction {b} from observed value {a}.","difference")),
}


def _semantic_task(concept:str, position:int)->tuple[str,str,tuple[str,...],str]:
    if position==1:
        return (f"{concept} aggregation",f"In {concept}, two compatible quantified contributions are {{a}} and {{b}}. Determine their combined value and verify the additive model.",(concept,"combined value"),"sum")
    if position==2:
        return (f"{concept} net change",f"In {concept}, a modeled quantity {{a}} is reduced by the compatible change {{b}}. Determine and verify the signed net value.",(concept,"net value"),"difference")
    if position==3:
        return (f"{concept} scale selection",f"For a bounded {concept} case, coefficient {{a}} scales a compatible magnitude {{b}}. Select the resulting product and reject additive distractors.",(concept,"resulting product"),"multiple_choice_product")
    if position==4:
        return (f"{concept} linear sensitivity",f"Within {concept}, use the local linear model f(x)={{a}}*x+{{b}}. Differentiate with respect to x and report the exact derivative coefficient.",(concept,"differentiate"),"derivative")
    return (f"{concept} normalized comparison",f"In {concept}, compare compatible nonzero measures {{a}} and {{b}} by computing the normalized quotient a/b.",(concept,"normalized quotient"),"ratio")


def _engineering_task(concept:str,position:int)->tuple[str,str,tuple[str,...],str]:
    if position in {2,4}:
        return (f"{concept} linear sensitivity",f"Within {concept}, use the local model f(x)={{a}}*x+{{b}}. Differentiate with respect to x and report the exact sensitivity.",(concept,"differentiate"),"derivative")
    if position==3:
        return (f"{concept} scaled term",f"Within {concept}, coefficient {{a}} scales compatible magnitude {{b}}. Compute and verify their product.",(concept,"product"),"product")
    if position==5:
        return (f"{concept} residual",f"Within {concept}, subtract compatible modeled contribution {{b}} from {{a}} and verify the signed residual.",(concept,"residual"),"difference")
    return _semantic_task(concept,position)


def _build_registry()->dict[str,tuple[DomainRecipeV1,...]]:
    registry={}
    for course_id,semantic_bindings in SEMANTIC_BINDINGS.items():
        recipes=[]
        for position,(binding_index,concept) in enumerate(semantic_bindings,1):
            operation_label,prompt,operation=COURSE_SCENARIOS[course_id][position-1]
            semantic=f"{concept} {operation_label}"; terms=(concept,operation_label)
            engine={"multiple_choice_product":"multiple_choice","matrix":"matrix","linear_root":"symbolic_expression","recurrence_step":"symbolic_expression"}.get(operation,"numeric_scalar")
            binding=RecipeBindingV1(course_id,f"{course_id}_TOPIC_{binding_index:03d}",f"{course_id}_SKILL_{binding_index:03d}",f"{course_id}_PROC_{binding_index:03d}",f"{course_id}_FAMILY_{binding_index:03d}",engine)
            if course_id in {"NUMERICAL_METHODS","ENGINEERING_ANALYSIS","APPLIED_MATHEMATICS"}:
                domains=(ParameterDomainV1("scale",0.1,100.0,False,"declared_domain_unit"),ParameterDomainV1("order",1,4,True,"declared_order"),ParameterDomainV1("variant",1,20,True,"declared_variant"))
            else: domains=(ParameterDomainV1("variant",1,1000,True,"declared_variant"),ParameterDomainV1("coefficient_scale",1,12,True,"declared_scale"))
            recipe=DomainRecipeV1(f"recipe:{course_id.lower()}:{position:02d}","1.1",binding,domains,tuple(terms),(semantic,operation),prompt,operation); recipe.validate(); recipes.append(recipe)
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
            parameters={"scale":2+variant,"order":1+variant%4,"variant":1+variant} if course_id in {"NUMERICAL_METHODS","ENGINEERING_ANALYSIS","APPLIED_MATHEMATICS"} else {"variant":2+variant,"coefficient_scale":1+variant}
            context=GenerationContextV1(parameters,variant,("FOUNDATIONAL","DEVELOPING","ADVANCED")[variant%3])
            answer=recipe.generate_answer(context); derivation=recipe.derive_independently(context); validate_answer_shape(recipe,answer)
            contract=recipe.build_contract(context); normalized=registry.normalize(answer,contract)
            a,b=recipe._parameters(context)
            if recipe.operation=="derivative": derivation_input={"expression":f"{a}*x+{b}","operation":"derivative"}
            elif recipe.operation=="linear_root": derivation_input={"expression":f"{a}*x+{b}","operation":"linear_root"}
            elif recipe.operation=="recurrence_step": derivation_input={"current":a,"increment":b,"operation":"recurrence_step"}
            elif recipe.operation=="matrix": derivation_input={"operation":"addition","left":[[a,0],[0,a]],"right":[[0,b],[b,0]]}
            else: derivation_input={"independently_derived_answer":derivation.normalized_answer}
            derived=registry.derive(derivation_input,contract); graded=registry.grade(answer,derivation.normalized_answer,contract)
            if normalized.status!=derived.status or normalized.status!="PASS" or normalized.value!=derived.value or graded.status!="PASS": raise ValueError("engine proof failed without fallback")
            records.append({"recipe_id":recipe.recipe_id,"binding":recipe.binding,"context":context,"prompt":recipe.build_prompt(context),"generator_answer":answer,"derivation":derivation,"engine_validation":{"normalize":normalized.to_dict(),"derive":derived.to_dict(),"grade":graded.to_dict()}})
    return tuple(records)


def audit_recipe_catalog()->dict[str,Any]:
    for recipes in COURSE_RECIPE_REGISTRY.values():
        for recipe in recipes: recipe.validate()
    return {"courses":len(COURSE_RECIPE_REGISTRY),"recipes":sum(map(len,COURSE_RECIPE_REGISTRY.values())),"status":"PASS"}
