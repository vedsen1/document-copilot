from __future__ import annotations

from typing import List


def reciprocal_rank_fusion(rank_lists: List[List[str]], k: int = 60) -> List[str]:
    """Simple RRF implementation.

    rank_lists: list of lists containing item ids in ranked order (best->worst)
    returns: fused ranking (ids)
    """
    scores = {}
    for rl in rank_lists:
        for rank, item in enumerate(rl, start=1):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + rank)

    # sort by descending score then preserve deterministic tie-break via item
    fused = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    return [item for item, _ in fused]

