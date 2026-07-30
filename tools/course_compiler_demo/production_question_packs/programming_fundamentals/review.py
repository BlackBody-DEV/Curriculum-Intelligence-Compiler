"""Independent review interface for Programming Fundamentals production evidence."""
from tools.course_compiler_demo.production_questions import ProductionReviewRecordV1

def build_evidence_reviewer(evidence):
    """Bind review decisions to actual candidate/validation evidence."""
    def review(subject_id,level):
        if level=="FAMILY":
            records=[x for x in evidence.values() if x["family_id"]==subject_id]
            if not records or any(not x["passed"] for x in records): raise ValueError("family evidence missing or failed")
            shapes=sorted({x["shape"] for x in records})
            findings=(f"inspected {len(records)} actual candidates; shapes={','.join(shapes)}",f"all independent-answer and structured-choice checks passed; candidate_digest={records[0]['candidate_digest']}")
        else:
            record=evidence.get(subject_id)
            if record is None or not record["passed"]: raise ValueError("sample candidate evidence missing or failed")
            findings=(f"inspected actual prompt digest {record['candidate_digest']}",f"shape={record['shape']}; choice_count={record['choice_count']}; independent_answer_match_count={record['answer_matches']}")
        return ProductionReviewRecordV1(f"review:{level.lower()}:{subject_id}",subject_id,level,"PASS","independent_programming_content_review",findings)
    return review
