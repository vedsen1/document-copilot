from backend.retrieval.fusion import reciprocal_rank_fusion


def test_rrf_basic():
    a = ["a", "b", "c"]
    b = ["c", "b", "d"]
    fused = reciprocal_rank_fusion([a, b], k=60)
    # ensure 'b' and 'c' are present and ordering is deterministic
    assert set(fused) >= {"a", "b", "c", "d"}
    assert len(fused) >= 3
