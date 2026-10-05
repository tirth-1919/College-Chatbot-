from backend.app.knowledge.ml import embedding_service, hybrid_score
from backend.app.knowledge.semantic_cache import SemanticCache
from backend.app.knowledge.rag import rag_engine
from backend.app.knowledge.confidence import confidence_gate, verify_claims

def test_embedding_service_returns_normalized_vector_without_tenant_authority():
    vector = embedding_service.encode("library facilities")
    assert vector
    assert len(vector) > 8
    assert abs(sum(x * x for x in vector) - 1.0) < 0.01

def test_hybrid_score_exposes_semantic_and_reranker_signals():
    combined, semantic, reranker = hybrid_score("library facilities", "library facilities and reading room", 0.5)
    assert 0 <= combined <= 1
    assert -1 <= semantic <= 1
    assert reranker >= 0

def test_cache_invalidation_is_tenant_scoped():
    cache = SemanticCache()
    cache.set("same question", "A", college_id="college-a")
    cache.set("same question", "B", college_id="college-b")
    cache.invalidate_college("college-a")
    assert cache.get("same question", college_id="college-a") is None
    assert cache.get("same question", college_id="college-b") == "B"


def test_rag_requires_tenant_before_retrieval():
    assert rag_engine.search(None, "library facilities", college_id=None) == []

def test_confidence_gate_fails_conflicts_and_unsupported_claims():
    score = confidence_gate.score(.9, .9, .9, .9, 1.0, 1.0, conflict=True)
    assert confidence_gate.decision(score, verified=True, conflict=True) != "VERIFIED"
    result = verify_claims("The library has 50000 books.", [{"details": "The library has books."}])
    assert result["verified"] is False
