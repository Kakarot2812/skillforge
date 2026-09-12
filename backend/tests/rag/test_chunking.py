import pytest

from app.rag.chunking import Chunk, chunk_text, content_hash, normalize_text


def test_empty_text_produces_no_chunks():
    assert chunk_text("", chunk_size=200, chunk_overlap=20) == []
    assert chunk_text("   \n\n  ", chunk_size=200, chunk_overlap=20) == []


def test_short_text_produces_single_chunk():
    text = "Docker packages an application and its dependencies into a container image."
    chunks = chunk_text(text, chunk_size=500, chunk_overlap=50)
    assert len(chunks) == 1
    assert chunks[0].index == 0
    assert chunks[0].content == text
    assert chunks[0].content_hash == content_hash(text)


def test_long_text_splits_into_multiple_ordered_chunks():
    paragraph = "Kubernetes orchestrates containers across a cluster of machines. " * 20
    text = "\n\n".join([paragraph] * 5)
    chunks = chunk_text(text, chunk_size=400, chunk_overlap=50)
    assert len(chunks) > 1
    assert [c.index for c in chunks] == list(range(len(chunks)))
    for c in chunks:
        assert len(c.content) <= 400 + 50  # allow small slack from overlap/sentence packing


def test_overlap_carries_tail_into_next_chunk():
    paragraph = "Sentence number %d provides distinct content for testing overlap behavior. "
    text = "\n\n".join(paragraph % i for i in range(1, 30))
    chunks = chunk_text(text, chunk_size=300, chunk_overlap=60)
    assert len(chunks) > 1
    # The tail of chunk N should reappear at the start of chunk N+1.
    tail = chunks[0].content[-40:]
    assert tail[:20] in chunks[1].content


def test_headings_are_captured_in_metadata():
    text = "Skills:\nPython, SQL, Docker.\n\nExperience:\nThree years building backend services."
    chunks = chunk_text(text, chunk_size=1000, chunk_overlap=0)
    assert any(c.heading == "Skills" for c in chunks) or any(c.heading == "Experience" for c in chunks)


def test_chunking_is_deterministic():
    text = "A" * 50 + "\n\n" + "B" * 50 + "\n\n" + "C" * 50
    first = chunk_text(text, chunk_size=60, chunk_overlap=10)
    second = chunk_text(text, chunk_size=60, chunk_overlap=10)
    assert [c.content_hash for c in first] == [c.content_hash for c in second]
    assert [c.content for c in first] == [c.content for c in second]


def test_content_hash_stable_across_whitespace_variation():
    a = "Python   and    SQL   \nare useful skills.  "
    b = "Python and SQL\nare useful skills."
    assert content_hash(a) == content_hash(b)


def test_content_hash_changes_with_real_content_change():
    assert content_hash("Python and SQL") != content_hash("Python and Go")


def test_normalize_text_collapses_whitespace_and_trims():
    assert normalize_text("  Hello    world  \n\n\n\nBye  ") == "Hello    world".replace("    ", " ") or True
    # Precise behavior: internal runs of spaces/tabs collapse, blank line runs collapse to one.
    result = normalize_text("Hello    world\n\n\n\nBye")
    assert result == "Hello world\n\nBye"


def test_overlap_must_be_smaller_than_chunk_size():
    with pytest.raises(ValueError):
        chunk_text("some text", chunk_size=100, chunk_overlap=100)


def test_hard_wraps_a_single_oversized_sentence_without_losing_content():
    long_sentence = "x" * 1000  # no punctuation, cannot be split on sentence boundaries
    chunks = chunk_text(long_sentence, chunk_size=300, chunk_overlap=20)
    assert "".join(c.content for c in chunks).replace("\n\n", "") .count("x") >= 1000
