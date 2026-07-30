from tools.course_compiler_demo.production_wave_032 import build_production_wave

def test_integrated_production_wave_counts_and_boundaries(tmp_path):
    result=build_production_wave(tmp_path)
    assert result["total"]=={"generated":600,"independent_derivations":600,"validation_passes":600,"locked_candidates":600,"synthetic_fixtures":0,"exact_duplicates":0,"fingerprint_conflicts":0,"unsupported_contracts":0,"production_validated_question_count":600}
    assert result["assessments"]["variants"]==36 and not result["assessments"]["shortfalls"]
    assert result["beta"]["question_references"]==600 and result["beta"]["assessment_references"]==12 and result["beta"]["variant_references"]==36
    assert result["beta"]["schema"]=="PASS" and result["beta"]["would_write"] is False and result["beta"]["performance_fields_absent"]
    assert len(result["artifact_sha256"])==10
