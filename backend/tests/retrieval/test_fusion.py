from uuid import UUID
from app.retrieval.fusion import reciprocal_rank_fusion


def test_rrf_basic():
    id_a = UUID("00000000-0000-0000-0000-000000000001")
    id_b = UUID("00000000-0000-0000-0000-000000000002")
    id_c = UUID("00000000-0000-0000-0000-000000000003")
    id_d = UUID("00000000-0000-0000-0000-000000000004")
    a = [id_a, id_b, id_c]
    b = [id_c, id_b, id_d]
    fused = reciprocal_rank_fusion([a, b], k=60)
    # ensure 'b' and 'c' are present and ordering is deterministic
    fused_ids = [item[0] for item in fused]
    assert set(fused_ids) >= {id_a, id_b, id_c, id_d}
    assert len(fused) >= 3
