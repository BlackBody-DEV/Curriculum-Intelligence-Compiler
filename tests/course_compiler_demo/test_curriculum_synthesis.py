import pytest
from tools.course_compiler_demo.source_corpus.synthesis import *
def c(i,title,source="s1",**kw): return SynthesisCandidate(i,"TOPIC",title,source,("claim:"+i,),.8,**kw)
def test_dedup_weighting_coverage_and_gaps():
 items=(c("1","Linear Equations"),c("2","Solving linear equations","s2",synonym_key="linear equations"))
 r=synthesize(items,{"claim:1","claim:2"},{"s1":1,"s2":.5},{"TOPIC":{"linear equations","quadratics"},"UNIT":set(),"MICRO_SKILL":set(),"PROCEDURE":set(),"ASSESSMENT_OBJECTIVE":set()})
 assert len(r.nodes)==1 and r.nodes[0].reconciliation=="SYNONYM_RECONCILIATION" and r.completeness=="SYNTHESIZED_WITH_GAPS" and r.coverage.topic_coverage==.5
 assert r.deterministic_sha256==synthesize(items,{"claim:1","claim:2"},{"s1":1,"s2":.5},{"TOPIC":{"linear equations","quadratics"},"UNIT":set(),"MICRO_SKILL":set(),"PROCEDURE":set(),"ASSESSMENT_OBJECTIVE":set()}).deterministic_sha256
def test_conflicts_preserved_never_silently_resolved():
 r=synthesize((c("1","Vectors",hierarchy_path=("A",)),c("2","Vectors","s2",hierarchy_path=("B",))),{"claim:1","claim:2"},{"s1":1,"s2":1},{"TOPIC":{"vectors"}})
 assert not r.nodes and r.completeness=="CONFLICT_BLOCKED" and r.conflicts[0].conflict_class=="TOPIC_HIERARCHY_CONFLICT" and r.conflicts[0].resolution_state=="UNRESOLVED"
def test_unresolved_evidence_and_weights_fail_closed():
 with pytest.raises(SynthesisError): synthesize((c("1","T"),),{"other"},{"s1":1},{})
 with pytest.raises(SynthesisError): synthesize((c("1","T"),),{"claim:1"},{"s1":0},{})
def test_all_conflict_classes_declared(): assert len(ConflictClass)==10
def test_empty_input_is_explicitly_insufficient(): assert synthesize((),set(),{},{}).completeness=="INSUFFICIENT_EVIDENCE"
def test_every_simultaneous_conflict_for_every_unordered_pair_is_preserved():
 items=(c("1","Vectors",hierarchy_path=("A",),rights="APPROVED"),c("2","Vectors","s2",hierarchy_path=("B",),rights="DENIED"),c("3","Vectors","s3",hierarchy_path=("C",),rights="RESTRICTED"))
 r=synthesize(items,{"claim:1","claim:2","claim:3"},{"s1":1,"s2":1,"s3":1},{"TOPIC":{"vectors"}})
 assert len(r.conflicts)==6
 assert {(x.candidate_ids,x.conflict_class) for x in r.conflicts}=={(("1","2"),"TOPIC_HIERARCHY_CONFLICT"),(("1","2"),"RIGHTS_CONFLICT"),(("1","3"),"TOPIC_HIERARCHY_CONFLICT"),(("1","3"),"RIGHTS_CONFLICT"),(("2","3"),"TOPIC_HIERARCHY_CONFLICT"),(("2","3"),"RIGHTS_CONFLICT")}
 assert all(x.evidence_claim_ids==tuple("claim:"+i for i in x.candidate_ids) and x.resolution_state=="UNRESOLVED" for x in r.conflicts)

def test_terminology_conflict_is_preserved_without_breaking_explicit_synonyms():
 conflicting=(c("1","Work",terminology_context="energy transferred by force"),c("2","Work","s2",terminology_context="assigned learning task"))
 r=synthesize(conflicting,{"claim:1","claim:2"},{"s1":1,"s2":1},{"TOPIC":{"work"}})
 assert not r.nodes and r.completeness=="CONFLICT_BLOCKED"
 assert [(x.conflict_class,x.candidate_ids,x.evidence_claim_ids,x.resolution_state) for x in r.conflicts]==[("TERMINOLOGY_CONFLICT",("1","2"),("claim:1","claim:2"),"UNRESOLVED")]
 synonyms=(c("3","Linear Equations",terminology_context="one-variable algebra"),c("4","Solving linear equations","s2",synonym_key="linear equations",terminology_context="one variable algebra"))
 reconciled=synthesize(synonyms,{"claim:3","claim:4"},{"s1":1,"s2":1},{"TOPIC":{"linear equations"}})
 assert not reconciled.conflicts and len(reconciled.nodes)==1 and reconciled.nodes[0].reconciliation=="SYNONYM_RECONCILIATION"
