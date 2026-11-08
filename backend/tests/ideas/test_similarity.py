
from app.ideas.similarity import find_similar


def test_identical_text():
    corpus = [
        (1, "machine learning based disease prediction system")
    ]

    result = find_similar(
        "machine learning based disease prediction system",
        corpus
    )

    assert len(result) == 1
    assert result[0][0] == 1
    assert result[0][1] == 1.0


def test_unrelated_text():
    corpus = [
        (1, "online food ordering application")
    ]

    result = find_similar(
        "satellite image classification using deep learning",
        corpus
    )

    assert result == []


def test_empty_text():
    assert find_similar("", [(1, "sample idea")]) == []


def test_empty_corpus():
    assert find_similar("sample idea", []) == []


def test_stop_words_only():
    corpus = [
        (1, "the and is")
    ]

    result = find_similar("the and is", corpus)

    assert result == []


def test_maximum_three_matches():
    corpus = [
        (1, "machine learning disease prediction"),
        (2, "machine learning disease prediction"),
        (3, "machine learning disease prediction"),
        (4, "machine learning disease prediction"),
    ]

    result = find_similar(
        "machine learning disease prediction",
        corpus
    )

    assert len(result) == 3
