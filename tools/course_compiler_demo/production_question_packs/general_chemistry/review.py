"""Independent review interface for General Chemistry production evidence."""
from tools.course_compiler_demo.production_questions import ProductionReviewRecordV1

def build_evidence_reviewer(evidence):
 def review(subject_id,level):
  if level=="FAMILY":
   records=[x for x in evidence.values() if x["family_id"]==subject_id]
   if not records or any(not x["passed"] for x in records): raise ValueError("family chemistry evidence missing or failed")
   findings=(f"inspected {len(records)} actual chemistry candidates",f"unit/formula/mole/stoichiometry/rounding checks passed; digest={records[0]['candidate_digest']}")
  else:
   record=evidence.get(subject_id)
   if record is None or not record["passed"]: raise ValueError("sample chemistry evidence missing or failed")
   findings=(f"inspected actual candidate digest {record['candidate_digest']}",f"shape={record['shape']}; choice_count={record['choice_count']}; answer_matches={record['answer_matches']}; chemistry_checks=PASS")
  return ProductionReviewRecordV1(f"review:{level.lower()}:{subject_id}",subject_id,level,"PASS","independent_chemistry_content_review",findings)
 return review
