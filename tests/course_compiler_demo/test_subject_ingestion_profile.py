import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from tools.course_compiler_demo.package.release_package_emitter import emit_release_package
from tools.course_compiler_demo.profiles.subject_profile_loader import (
    ProfileValidationError,
    SubjectProfileRunError,
    build_profile_run,
    load_profile,
    safe_output_dir,
    validate_profile,
    write_profile_run,
)


ROOT = Path(__file__).resolve().parents[2]
PROFILE = ROOT / "tools/course_compiler_demo/profiles/physics_intro_mechanics_v1.json"
SOURCE = ROOT / "tools/course_compiler_demo/sample_inputs/physics_intro_mechanics_profile_demo.txt"
CLI = ROOT / "tools/course_compiler_demo/run_subject_profile_ingestion.py"
SELECTED = "apply_newtons_second_law_1d"


def load_json(path: Path):
    return json.loads(path.read_text())


def physics_profile():
    return load_profile(PROFILE)


def physics_source():
    return SOURCE.read_text()


def build_physics():
    return build_profile_run(
        profile=physics_profile(),
        source_text=physics_source(),
        source_path=SOURCE,
        selected_micro_skill=SELECTED,
    )


def test_physics_profile_validates():
    profile = physics_profile()
    assert profile["profile_status"] == "compiler_profile_review_pending"
    assert profile["non_live_boundary"]["eligible_for_alpha_import"] is False


def test_physics_source_is_interpreted_as_physics():
    result = build_physics()
    assert result.outputs["source_interpretation.json"]["detected_subject"] == "PHYSICS"


def test_physics_course_level_is_detected():
    result = build_physics()
    assert result.outputs["source_interpretation.json"]["detected_course_level"] == "INTRO_PHYSICS_MECHANICS"


def test_open_textbook_course_level_signal_is_accepted(tmp_path):
    text = "\n".join(
        [
            "SOURCE TITLE: University Physics Volume 1, Section 5.3 Newton's Second Law",
            "AUTHOR OR INSTITUTION: OpenStax",
            "This Physics open textbook section is part of University Physics Volume 1.",
            "The net external force is the vector sum of all external forces.",
            "Newton's Second Law is often written as F net = m a.",
            "The vector equation can be written as component equations.",
            "A force may be resolved into x - and y -components before applying the law.",
        ]
    )
    result = build_profile_run(
        profile=physics_profile(),
        source_text=text,
        source_path=tmp_path / "openstax_excerpt.txt",
        selected_micro_skill=SELECTED,
    )
    assert result.outputs["source_interpretation.json"]["detected_course_level"] == "INTRO_PHYSICS_MECHANICS"
    assert result.release_seed["selected_micro_skill_code"] == SELECTED


def test_required_three_topics_are_extracted():
    topics = build_physics().outputs["topic_candidates.json"]["topic_candidates"]
    assert [topic["topic_code"] for topic in topics] == ["vectors", "net_force", "newtons_laws"]
    assert all(topic["source_evidence"] for topic in topics)


def test_required_three_micro_skills_are_extracted():
    skills = build_physics().outputs["micro_skill_candidates.json"]["micro_skill_candidates"]
    assert [skill["micro_skill_code"] for skill in skills] == [
        "resolve_force_components_2d",
        "compute_net_force_1d",
        "apply_newtons_second_law_1d",
    ]
    assert all(skill["source_evidence"] for skill in skills)


def test_dependency_chain_present_and_acyclic():
    deps = build_physics().outputs["dependency_candidates.json"]["dependency_candidates"]
    assert [(dep["from_micro_skill_code"], dep["to_micro_skill_code"]) for dep in deps] == [
        ("resolve_force_components_2d", "compute_net_force_1d"),
        ("compute_net_force_1d", "apply_newtons_second_law_1d"),
    ]
    validate_profile(physics_profile())


def test_selected_newton_skill_creates_release_seed():
    seed = build_physics().release_seed
    assert seed["selected_micro_skill_code"] == SELECTED
    assert seed["subject_code"] == "PHYSICS"
    assert seed["prerequisite_micro_skill_codes"] == ["compute_net_force_1d"]


def test_seed_contains_candidates_and_packages():
    seed = build_physics().release_seed
    assert seed["procedure_candidates"]
    assert len(seed["question_candidates"]) >= 2
    assert seed["generation_family_candidates"]
    assert seed["practice_module_package"]["question_ids"]
    assert seed["practice_assessment_package"]["question_ids"]
    assert seed["performance_tracking_package"]["tracked_question_ids"]


def test_source_evidence_and_rights_metadata_are_preserved():
    result = build_physics()
    package = result.outputs["curriculum_extraction_package.json"]
    assert package["source_evidence"]
    assert result.release_seed["rights_summary"]["rights_status"] == "owned_by_axiomiq"
    assert result.release_seed["rights_summary"]["privacy_status"] == "non_private"


def test_release_emitter_accepts_generated_seed(tmp_path):
    result = emit_release_package(
        source_payload=build_physics().release_seed,
        output_dir=tmp_path,
        package_id="PHYSICS_INTRO_MECHANICS_NEWTON_SECOND_LAW_INTERNAL_V1",
    )
    package = load_json(result.package_path)
    assert package["subject_code"] == "PHYSICS"
    assert package["selected_micro_skill_code"] == SELECTED


def test_emitted_package_remains_non_live_and_review_pending(tmp_path):
    result = emit_release_package(
        source_payload=build_physics().release_seed,
        output_dir=tmp_path,
        package_id="PHYSICS_INTRO_MECHANICS_NEWTON_SECOND_LAW_INTERNAL_V1",
    )
    package = load_json(result.package_path)
    assert package["package_status"] == "compiler_non_live_review_pending"
    assert package["integration_boundary"]["eligible_for_alpha_import"] is False
    assert package["integration_boundary"]["adaptive_platform_write_performed"] is False


def generic_algebra_profile():
    profile = copy.deepcopy(physics_profile())
    profile["profile_id"] = "ALGEBRA_I_PROFILE_V1"
    profile["subject_code"] = "MATHEMATICS"
    profile["subject_name"] = "Mathematics"
    profile["supported_course_levels"] = ["ALGEBRA_I"]
    profile["output_names"] = {
        "release_seed": "algebra_i_release_seed_v1.json",
        "markdown_report": "ALGEBRA_I_PROFILE_RUN_V1.md",
    }
    profile["topic_rules"] = [
        {"topic_code": "linear_equations", "topic_name": "Linear Equations", "sequence_order": 1, "evidence_patterns": ["linear equation", "solve for x"]}
    ]
    profile["micro_skill_rules"] = [
        {
            "micro_skill_code": "solve_one_step_equation",
            "micro_skill_name": "Solve one-step equations",
            "topic_code": "linear_equations",
            "prerequisite_micro_skill_codes": [],
            "evidence_patterns": ["solve for x", "one-step equation"],
        }
    ]
    profile["dependency_rules"] = []
    profile["procedure_candidate_templates"] = [
        {"micro_skill_code": "solve_one_step_equation", "procedure_id": "PROC_ALGEBRA_ONE_STEP_001", "description": "Undo the operation to solve for x.", "steps": ["Identify the operation.", "Apply the inverse operation."]}
    ]
    profile["question_candidate_templates"] = [
        {"micro_skill_code": "solve_one_step_equation", "question_id": "Q_ALGEBRA_ONE_STEP_001", "prompt": "Solve x + 3 = 8.", "answer": {"value": 5}, "question_type": "numeric"}
    ]
    profile["generation_family_templates"] = [
        {"micro_skill_code": "solve_one_step_equation", "family_id": "GF_ALGEBRA_ONE_STEP_001", "family_type": "one_step_equation", "variable_fields": ["constant"], "variation_rules": {"constant": "Use integer constants."}}
    ]
    return profile


def test_temporary_second_subject_profile_proves_genericity(tmp_path):
    profile = generic_algebra_profile()
    text = "Subject: MATHEMATICS. Course-level signal: ALGEBRA_I. Topic: linear equation. Students solve for x in a one-step equation."
    result = build_profile_run(
        profile=profile,
        source_text=text,
        source_path=tmp_path / "algebra_source.txt",
        selected_micro_skill="solve_one_step_equation",
    )
    assert result.release_seed["subject_code"] == "MATHEMATICS"
    assert result.release_seed["selected_micro_skill_code"] == "solve_one_step_equation"
    assert "algebra_i_release_seed_v1.json" in result.outputs


def test_duplicate_ids_fail():
    profile = physics_profile()
    profile["topic_rules"].append(copy.deepcopy(profile["topic_rules"][0]))
    with pytest.raises(ProfileValidationError):
        validate_profile(profile)


def test_unknown_dependency_fails():
    profile = physics_profile()
    profile["dependency_rules"][0]["from_micro_skill_code"] = "missing_skill"
    with pytest.raises(ProfileValidationError):
        validate_profile(profile)


def test_dependency_cycle_fails():
    profile = physics_profile()
    profile["dependency_rules"].append(
        {
            "from_micro_skill_code": "apply_newtons_second_law_1d",
            "to_micro_skill_code": "resolve_force_components_2d",
        }
    )
    with pytest.raises(ProfileValidationError):
        validate_profile(profile)


def test_missing_selected_skill_fails():
    with pytest.raises(SubjectProfileRunError):
        build_profile_run(
            profile=physics_profile(),
            source_text=physics_source(),
            source_path=SOURCE,
            selected_micro_skill="missing_skill",
        )


def test_subject_profile_mismatch_fails(tmp_path):
    with pytest.raises(SubjectProfileRunError):
        build_profile_run(
            profile=physics_profile(),
            source_text="Subject: CHEMISTRY. Course-level signal: INTRO_PHYSICS_MECHANICS.",
            source_path=tmp_path / "bad.txt",
            selected_micro_skill=SELECTED,
        )


def test_unauthorized_canonical_or_live_state_fails():
    profile = physics_profile()
    profile["non_live_boundary"]["live_eligible"] = True
    with pytest.raises(ProfileValidationError):
        validate_profile(profile)


def test_output_inside_adaptive_platform_fails():
    with pytest.raises(SubjectProfileRunError):
        safe_output_dir("/Users/fanarichardson/adaptive-platform/profile-output")


def test_invalid_run_leaves_no_partial_output(tmp_path):
    output = tmp_path / "out"
    completed = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--profile",
            str(PROFILE),
            "--input",
            str(SOURCE),
            "--selected-micro-skill",
            "missing_skill",
            "--output",
            str(output),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert completed.returncode != 0
    assert not output.exists()


def test_deterministic_profile_run_semantic_digest():
    one = build_physics()
    two = build_physics()
    assert one.semantic_digest == two.semantic_digest


def test_cli_exits_nonzero_on_invalid_profile(tmp_path):
    invalid_profile = tmp_path / "invalid.json"
    invalid_profile.write_text("{bad json")
    completed = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--profile",
            str(invalid_profile),
            "--input",
            str(SOURCE),
            "--selected-micro-skill",
            SELECTED,
            "--output",
            str(tmp_path / "out"),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert completed.returncode != 0


def test_cli_produces_required_profile_run_files(tmp_path):
    output = tmp_path / "physics_profile_run"
    completed = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--profile",
            str(PROFILE),
            "--input",
            str(SOURCE),
            "--selected-micro-skill",
            SELECTED,
            "--output",
            str(output),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    assert "SUBJECT_PROFILE_INGESTION_COMPLETE" in completed.stdout
    assert sorted(path.name for path in output.iterdir()) == sorted(
        [
            "source_document.json",
            "source_interpretation.json",
            "source_feature_flags.json",
            "curriculum_extraction_package.json",
            "topic_candidates.json",
            "micro_skill_candidates.json",
            "dependency_candidates.json",
            "content_gaps.json",
            "physics_intro_mechanics_release_seed_v1.json",
            "PHYSICS_INTRO_MECHANICS_PROFILE_RUN_V1.md",
            "profile_validation_v1.json",
        ]
    )


def test_write_profile_run_writes_only_expected_names(tmp_path):
    result = build_physics()
    write_profile_run(result, tmp_path)
    assert "physics_intro_mechanics_release_seed_v1.json" in {path.name for path in tmp_path.iterdir()}
