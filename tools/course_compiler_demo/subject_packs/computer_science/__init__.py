"""Noncanonical computer-science reference pack and expanded catalog."""
from .catalog import (COURSE_IDS, ENGINE_ALLOCATIONS, build_computer_science_course_catalog,
    validate_computer_science_course_catalog)
from .pack import build_programming_fundamentals_pack, validate_programming_fundamentals_pack
__all__=["COURSE_IDS","ENGINE_ALLOCATIONS","build_computer_science_course_catalog",
    "validate_computer_science_course_catalog","build_programming_fundamentals_pack",
    "validate_programming_fundamentals_pack"]
