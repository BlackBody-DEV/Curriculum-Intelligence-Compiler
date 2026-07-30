"""Science, engineering, computer-science, and life-science recipes."""

from .catalog import COURSE_IDS, RECIPES, recipes_for_course, self_audit
from .model import DomainRecipe, RecipeBinding, RecipeResult
from .runtime_adapter import build_runtime, build_runtime_registry, to_runtime_recipe

__all__ = ["COURSE_IDS", "RECIPES", "DomainRecipe", "RecipeBinding", "RecipeResult", "build_runtime", "build_runtime_registry", "recipes_for_course", "self_audit", "to_runtime_recipe"]
