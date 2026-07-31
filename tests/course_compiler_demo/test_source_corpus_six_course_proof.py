from tools.course_compiler_demo.source_corpus.pipeline import (
    checkpoint_reference_course_corpora,
    compile_reference_course_corpora,
    reopen_reference_course_corpora,
)


def test_six_course_eighteen_source_pipeline_proof_is_complete_and_deterministic():
    first = compile_reference_course_corpora()
    second = compile_reference_course_corpora()
    assert first == second
    summary = first["summary"]
    assert summary["reference_courses"] == 6
    assert summary["source_documents_processed"] == 18
    assert summary["source_segments_processed"] == 144
    assert summary["curriculum_synthesis_packages"] == 6
    assert summary["generation_manifests"] == 6
    assert summary["generation_question_target"] == 1800
    assert summary["assessment_blueprints"] == 18
    assert summary["assessment_compiler_blueprints"] == 24
    assert summary["unsupported_candidates"] == 0
    assert summary["source_free_nodes"] == 0
    assert summary["silent_conflict_resolutions"] == 0
    assert summary["canonical_authority"] is False


def test_required_source_population_and_per_course_outputs_are_present():
    result = compile_reference_course_corpora()
    source_types = result["summary"]["source_type_counts"]
    assert source_types["TEXT_NATIVE_PDF"] >= 2
    assert source_types["SYLLABUS"] >= 2
    assert source_types["STANDARDS_DOCUMENT"] >= 2
    assert source_types["QUESTION_BANK"] >= 2
    assert source_types["COURSE_DEFINITION_PACKAGE"] == 6
    required = {
        "normalized_source_corpus",
        "source_evidence_graph",
        "curriculum_extraction_package",
        "synthesized_curriculum_package",
        "conflict_report",
        "coverage_report",
        "proposed_canonical_mappings",
        "procedure_and_generation_requirement_package",
        "generation_manifest",
        "assessment_blueprints",
        "review_package",
    }
    assert len(result["courses"]) == 6
    for course in result["courses"]:
        assert required <= set(course)
        assert course["source_fixture_classification"] == "CURATED_INTERNAL_FIXTURE"
        assert len(course["normalized_source_corpus"]["documents"]) == 3
        assert len(course["assessment_blueprints"]) == 3
        assert len(course["assessment_blueprint_package"]["blueprints"]) == 4
        assert course["generation_manifest"]["requirements"][0]["requested_count"] == 300


def test_all_nodes_mappings_conflicts_and_reviews_remain_fail_closed():
    result = compile_reference_course_corpora()
    for course in result["courses"]:
        assert course["curriculum_extraction_package"]["unsupported_candidates"] == []
        assert all(
            node["evidence_claim_ids"]
            for node in course["synthesized_curriculum_package"]["nodes"]
        )
        assert course["conflict_report"] == {
            "conflicts": [],
            "conflict_count": 0,
            "silent_resolutions": 0,
        }
        mappings = course["proposed_canonical_mappings"]
        assert mappings["classification"] == "PROPOSED_NONAUTHORITATIVE_MAPPING"
        assert mappings["canonical_authority"] is False
        assert all(mapping["source_evidence"] for mapping in mappings["alignments"])
        assert course["review_report"]["passed"] is True
        assert course["review_report"]["action"] == "ACCEPT_SYNTHESIS_FOR_REVIEW"
        assert course["review_report"]["canonical_authority"] is False


def test_checkpoint_restart_and_reopen_preserve_every_output_hash(tmp_path):
    first = compile_reference_course_corpora()
    checkpoint = tmp_path / "wave066-checkpoint.json"
    checkpoint_hash = checkpoint_reference_course_corpora(checkpoint, first)
    reopened = reopen_reference_course_corpora(checkpoint)
    rebuilt = compile_reference_course_corpora()
    assert len(checkpoint_hash) == 64
    assert reopened["reopen_verified"] is True
    assert reopened["deterministic_sha256"] == first["deterministic_sha256"]
    assert rebuilt["deterministic_sha256"] == first["deterministic_sha256"]
    reopened.pop("reopen_verified")
    assert reopened == first
