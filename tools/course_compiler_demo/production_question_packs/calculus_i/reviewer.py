from tools.course_compiler_demo.production_questions import ProductionReviewRecordV1
def build_evidence_reviewer(evidence):
 def review(subject_id,level):
  records=[x for x in evidence.values() if x["family_id"]==subject_id] if level=="FAMILY" else ([evidence[subject_id]] if subject_id in evidence else [])
  if not records or any(not x["passed"] for x in records): raise ValueError("Calculus review evidence missing or failed")
  findings=(f"inspected {len(records)} validated candidate artifacts",f"candidate_digest={records[0]['candidate_digest']}; validation_digest={records[0]['validation_digest']}; choice_count={records[0]['choice_count']}; answer_matches={records[0]['answer_matches']}; numeric_matches={records[0]['numeric_matches']}")
  return ProductionReviewRecordV1(f"review:{level.lower()}:{subject_id}",subject_id,level,"PASS","calculus_i_independent_content_reviewer",findings)
 return review
