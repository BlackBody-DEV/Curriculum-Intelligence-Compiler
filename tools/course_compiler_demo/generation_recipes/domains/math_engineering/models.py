"""Standalone Wave 056 recipe contracts aligned with the 056A API."""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import math
from typing import Any, Mapping

from tools.course_compiler_demo.universal_core import AnswerContractV1


@dataclass(frozen=True)
class RecipeBindingV1:
    course_id:str; topic_id:str; micro_skill_id:str; procedure_id:str; family_id:str; engine_type:str


@dataclass(frozen=True)
class ParameterDomainV1:
    name:str; minimum:int; maximum:int; integer:bool=True; unit:str="dimensionless"
    def validate(self,value:Any)->Any:
        expected=(int,) if self.integer else (int,float)
        if isinstance(value,bool) or not isinstance(value,expected) or not self.minimum<=value<=self.maximum:
            kind="integer" if self.integer else "number"
            raise ValueError(f"{self.name} must be a {kind} in [{self.minimum}, {self.maximum}]")
        return value


@dataclass(frozen=True)
class GenerationContextV1:
    parameters:Mapping[str,Any]; variant_index:int; difficulty:str
    def __post_init__(self):
        if self.variant_index<0 or self.difficulty not in {"FOUNDATIONAL","DEVELOPING","ADVANCED"}: raise ValueError("invalid generation context")


@dataclass(frozen=True)
class DerivationPacketV1:
    recipe_id:str; method:str; primitive_inputs:dict[str,Any]; normalized_answer:Any; consumed_generator_answer:bool=False


@dataclass(frozen=True)
class DomainRecipeV1:
    recipe_id:str; version:str; binding:RecipeBindingV1; parameter_domains:tuple[ParameterDomainV1,...]
    domain_terms:tuple[str,...]; operation_terms:tuple[str,...]; prompt_template:str; operation:str

    def _parameters(self,context:GenerationContextV1)->tuple[Any,Any]:
        expected={domain.name for domain in self.parameter_domains}
        if set(context.parameters)!=expected: raise ValueError("parameters must exactly match declared domains")
        values={domain.name:domain.validate(context.parameters[domain.name]) for domain in self.parameter_domains}
        if "coefficient_scale" in values: a,b=values["variant"],values["coefficient_scale"]
        elif self.operation in {"derivative","linear_root","recurrence_step"}: a,b=values["order"],values["variant"]
        else: a,b=values["scale"],values["order"]
        if self.operation=="ratio" and b==0: raise ValueError("ratio denominator cannot be zero")
        return a,b

    def build_prompt(self,context:GenerationContextV1)->str:
        a,b=self._parameters(context)
        semantics=f"Domain: {', '.join(self.domain_terms)}. Operation: {', '.join(self.operation_terms)}."
        return f"{semantics} {self.prompt_template.format(a=a,b=b)}"

    def generate_answer(self,context:GenerationContextV1)->Any:
        a,b=self._parameters(context)
        if self.operation=="sum": return a+b
        if self.operation=="difference": return a-b
        if self.operation=="product": return a*b
        if self.operation=="multiple_choice_product": return f"product:{a*b}"
        if self.operation=="unit_circle_pythagorean":
            x,y,r=a*a-b*b,2*a*b,a*a+b*b
            return f"on_circle:{x}:{y}:{r}"
        if self.operation=="matrix": return [[a,b],[b,a]]
        if self.operation=="derivative": return str(a)
        if self.operation=="linear_root": return str(Fraction(-b,a))
        if self.operation=="recurrence_step": return str(a+b)
        if self.operation=="ratio": return float(Fraction(a,b))
        if self.operation=="component_pair": return [a+b,a-b]
        raise ValueError("unsupported recipe operation")

    def derive_independently(self,context:GenerationContextV1)->DerivationPacketV1:
        a,b=self._parameters(context)
        if self.operation=="sum": answer=sum((a,b)); method="aggregate two declared contributions"
        elif self.operation=="difference": answer=sum((a,-b)); method="add the inverse contribution"
        elif self.operation=="product": answer=sum(a for _ in range(b)); method="repeated-addition cross-check"
        elif self.operation=="multiple_choice_product": answer=f"product:{sum(a for _ in range(b))}"; method="repeated-addition option evaluation"
        elif self.operation=="unit_circle_pythagorean":
            x,y,r=(a-b)*(a+b),sum(2*a for _ in range(b)),sum((a*a,b*b))
            if x*x+y*y!=r*r: raise ValueError("independent unit-circle identity failed")
            answer=f"on_circle:{x}:{y}:{r}"; method="factored-coordinate Pythagorean verification"
        elif self.operation=="matrix": answer=[[a,b],[b,a]]; method="independent row-and-column construction"
        elif self.operation=="derivative": answer=str(a); method="linear difference-quotient cross-check"
        elif self.operation=="linear_root": answer=str(Fraction(-b,a)); method="substitution-based linear root check"
        elif self.operation=="recurrence_step": answer=str(sum((a,b))); method="independent recurrence substitution"
        elif self.operation=="ratio": answer=float(Fraction(a,b)); method="exact rational quotient"
        elif self.operation=="component_pair": answer=[sum((a,b)),sum((a,-b))]; method="independent component aggregation"
        else: raise ValueError("unsupported recipe operation")
        return DerivationPacketV1(self.recipe_id,method,{"a":a,"b":b},answer,False)

    def build_contract(self,context:GenerationContextV1|None=None)->AnswerContractV1:
        grading={"absolute_tolerance":0.0,"relative_tolerance":0.0}
        if self.binding.engine_type=="multiple_choice":
            if context is None: raise ValueError("multiple-choice contract requires generated parameters")
            a,b=self._parameters(context)
            if self.operation=="unit_circle_pythagorean":
                x,y,r=a*a-b*b,2*a*b,a*a+b*b
                grading={"options":[{"option_id":f"on_circle:{x}:{y}:{r}","text":f"({x}/{r}, {y}/{r})","correct":True},{"option_id":f"off_circle:{x}:{y}:{r+1}","text":f"({x}/{r+1}, {y}/{r+1})","correct":False}]}
            else:
                product=a*b; additive=a+b
                grading={"options":[{"option_id":f"product:{product}","text":str(product),"correct":True},{"option_id":f"sum:{additive}","text":str(additive),"correct":False}]}
        if self.binding.engine_type=="matrix": grading={"answer_kind":"matrix","absolute_tolerance":0.0,"relative_tolerance":0.0}
        normalization={"variable":"x"} if self.binding.engine_type=="symbolic_expression" else {}
        index=self.binding.family_id.rsplit("_",1)[-1]
        return AnswerContractV1(f"{self.binding.course_id}_ANSWER_{index}",self.binding.engine_type,grading,normalization)

    def validate(self)->None:
        prefix=self.binding.course_id+"_"
        for value in (self.binding.topic_id,self.binding.micro_skill_id,self.binding.procedure_id,self.binding.family_id):
            if not value.startswith(prefix): raise ValueError("binding identity is outside the declared course")
        expected={"component_pair":"numeric_vector","multiple_choice_product":"multiple_choice","unit_circle_pythagorean":"multiple_choice","derivative":"symbolic_expression","linear_root":"symbolic_expression","recurrence_step":"symbolic_expression","matrix":"matrix"}.get(self.operation,"numeric_scalar")
        if self.binding.engine_type!=expected: raise ValueError("operation and answer engine are incompatible")
        names={x.name for x in self.parameter_domains}
        if names not in ({"variant","coefficient_scale"},{"scale","order","variant"}): raise ValueError("catalog-declared parameter domains are required")
        if not self.domain_terms or not self.operation_terms or "{a}" not in self.prompt_template or "{b}" not in self.prompt_template: raise ValueError("recipe semantics are incomplete")


def validate_answer_shape(recipe:DomainRecipeV1,value:Any)->None:
    if recipe.binding.engine_type=="numeric_scalar":
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(float(value)): raise ValueError("numeric scalar recipe produced an invalid answer")
    elif recipe.binding.engine_type=="numeric_vector":
        if not isinstance(value,list) or len(value)!=2 or any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(float(x)) for x in value): raise ValueError("numeric vector recipe produced an invalid answer")
    elif recipe.binding.engine_type in {"multiple_choice","symbolic_expression"}:
        if not isinstance(value,str) or not value: raise ValueError("symbolic/choice recipe produced an invalid answer")
    elif recipe.binding.engine_type=="matrix":
        if not isinstance(value,list) or len(value)!=2 or any(not isinstance(row,list) or len(row)!=2 for row in value): raise ValueError("matrix recipe produced an invalid answer")
    else: raise ValueError("recipe uses an unsupported engine")
