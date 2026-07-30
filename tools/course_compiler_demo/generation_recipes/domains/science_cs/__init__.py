"""Science, engineering, computer-science, and life-science recipes."""

from .catalog import COURSE_IDS, RECIPES, recipes_for_course, self_audit, semantic_compatibility_manifest
from .model import DomainRecipe, RecipeBinding, RecipeResult
from .runtime_adapter import build_runtime, build_runtime_registry, compatible_family, to_runtime_recipe

__all__ = ["COURSE_IDS", "RECIPES", "DomainRecipe", "RecipeBinding", "RecipeResult", "build_runtime", "build_runtime_registry", "compatible_family", "recipes_for_course", "self_audit", "semantic_compatibility_manifest", "to_runtime_recipe"]
