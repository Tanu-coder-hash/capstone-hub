
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


DEFAULT_THRESHOLD = 0.8


def find_similar(
    text,
    corpus,
    threshold=DEFAULT_THRESHOLD,
    top_k=3
):
    """
    Return up to top_k (idea_id, score) pairs
    with similarity strictly above the threshold.

    corpus format:
    [(idea_id, idea_text), ...]
    """

    if not text or not text.strip() or not corpus:
        return []

    documents = [text] + [doc for _, doc in corpus]

    vectorizer = TfidfVectorizer(stop_words="english")

    try:
        matrix = vectorizer.fit_transform(documents)

    except ValueError:
        # Handles text containing only stop words
        return []

    scores = cosine_similarity(
        matrix[0:1],
        matrix[1:]
    ).ravel()

    ranked = sorted(
        zip((idea_id for idea_id, _ in corpus), scores),
        key=lambda pair: pair[1],
        reverse=True
    )

    return [
        (idea_id, round(float(score), 3))
        for idea_id, score in ranked[:top_k]
        if score > threshold
    ]
