import uuid

from app.rag.ranker import reciprocal_rank_fusion
from app.rag.schemas import RetrievedChunk


def make_chunk(chunk_id, title="T", content="C") -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        document_id=uuid.uuid4(),
        source_type="manual",
        source_id="doc-1",
        title=title,
        content=content,
        source_url=None,
        user_id=None,
        metadata={},
    )


def test_chunk_in_both_lists_outranks_chunk_in_one_list():
    a, b = uuid.uuid4(), uuid.uuid4()
    vector_results = [make_chunk(a), make_chunk(b)]
    fts_results = [make_chunk(a)]

    fused = reciprocal_rank_fusion(vector_results, fts_results, k=60)

    assert fused[0].chunk_id == a
    assert fused[0].fused_score > fused[1].fused_score
    assert fused[0].vector_rank == 1 and fused[0].fts_rank == 1
    assert fused[1].chunk_id == b
    assert fused[1].fts_rank is None


def test_disjoint_lists_are_merged_and_ordered_by_original_rank():
    a, b, c, d = uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    vector_results = [make_chunk(a), make_chunk(b)]
    fts_results = [make_chunk(c), make_chunk(d)]

    fused = reciprocal_rank_fusion(vector_results, fts_results, k=60)

    assert {c.chunk_id for c in fused} == {a, b, c, d}
    # Rank-1 entries from each list score equally and higher than rank-2 entries.
    assert fused[0].fused_score == fused[1].fused_score
    assert fused[0].fused_score > fused[2].fused_score


def test_empty_inputs_produce_empty_output():
    assert reciprocal_rank_fusion([], [], k=60) == []


def test_one_empty_list_falls_back_to_the_other():
    a = uuid.uuid4()
    fused = reciprocal_rank_fusion([make_chunk(a)], [], k=60)
    assert len(fused) == 1
    assert fused[0].chunk_id == a
    assert fused[0].fts_rank is None
    assert fused[0].vector_rank == 1


def test_smaller_k_amplifies_top_rank_dominance():
    a, b = uuid.uuid4(), uuid.uuid4()
    results = [make_chunk(a), make_chunk(b)]

    fused_small_k = reciprocal_rank_fusion(results, [], k=1)
    fused_large_k = reciprocal_rank_fusion(results, [], k=1000)

    ratio_small = fused_small_k[0].fused_score / fused_small_k[1].fused_score
    ratio_large = fused_large_k[0].fused_score / fused_large_k[1].fused_score
    assert ratio_small > ratio_large > 1.0


def test_fused_list_is_sorted_descending_by_score():
    ids = [uuid.uuid4() for _ in range(5)]
    vector_results = [make_chunk(i) for i in ids]
    fused = reciprocal_rank_fusion(vector_results, [], k=60)
    scores = [c.fused_score for c in fused]
    assert scores == sorted(scores, reverse=True)
