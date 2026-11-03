import time
from pathlib import Path

import numpy
import requests
from dotenv import load_dotenv
from openai import APIConnectionError, OpenAI, RateLimitError

EMBEDDING_MODEL = "text-embedding-3-large"
_EMBEDDING_BATCH = 512


def download(url, filename, replace=False):
    """Download the file (check if it already exists)"""
    if Path(filename).exists() and not replace:
        print(f"File {filename} already exists")
        return
    print(f"Downloading {url} to {filename}")
    response = requests.get(url)
    with open(filename, "wb") as f:
        f.write(response.content)


def playable_words(word_lists):
    """Unique playable words across every word length."""
    words = set()
    for lists in word_lists.values():
        if isinstance(lists, dict) and "playable" in lists:
            words.update(lists["playable"])
    return sorted(words)


def embeddings_path(language):
    """Path of the embedding archive for a language code, under data/."""
    return Path(__file__).resolve().parent / "data" / f"{language}_embeddings.npz"


def embed_words(words, filename, texts=None, replace=False, model=EMBEDDING_MODEL):
    """Embed words with OpenAI and store a numpy archive.

    The archive is row-aligned: `words[i]` was embedded from `texts[i]`
    into `embeddings[i]`. Vectors already stored for the same word, text,
    and model are kept.
    """
    filename = Path(filename)
    words, texts = _embedding_inputs(words, texts)
    saved = None if replace else _load_embeddings(filename)
    if saved is not None and _same_embeddings(saved, words, texts, model):
        print(f"File {filename} already exists")
        return filename

    reusable = _reusable_vectors(saved, model)
    missing = [
        (word, text) for word, text in zip(words, texts) if (word, text) not in reusable
    ]
    if missing:
        _load_env()
        print(f"Embedding {len(missing)} words with {model}")
        reusable.update(_fetch_embeddings(missing, model))

    embeddings = numpy.stack([reusable[word, text] for word, text in zip(words, texts)])
    filename.parent.mkdir(parents=True, exist_ok=True)
    numpy.savez(
        filename,
        words=numpy.array(words),
        texts=numpy.array(texts),
        embeddings=embeddings.astype(numpy.float32),
        model=numpy.array(model),
    )
    print(f"Wrote {len(words)} embeddings to {filename}")
    return filename


def _embedding_inputs(words, texts):
    words = list(words)
    if texts is None:
        texts = [word.lower() for word in words]
    elif len(texts) != len(words):
        raise ValueError("texts must line up with words")
    else:
        texts = [text.lower() for text in texts]

    pairs = {}
    for word, text in zip(words, texts):
        if word in pairs and pairs[word] != text:
            raise ValueError(f"Conflicting texts for {word}")
        pairs[word] = text
    ordered = sorted(pairs)
    return ordered, [pairs[word] for word in ordered]


def _load_env():
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def _load_embeddings(filename):
    if not filename.exists():
        return None
    try:
        with numpy.load(filename) as saved:
            return {
                "words": [str(word) for word in saved["words"].tolist()],
                "texts": [str(text) for text in saved["texts"].tolist()],
                "embeddings": numpy.array(saved["embeddings"], dtype=numpy.float32),
                "model": str(saved["model"].item()),
            }
    except Exception as exc:
        print(f"Could not read {filename} ({exc}); recomputing")
        return None


def _same_embeddings(saved, words, texts, model):
    return (
        saved["words"] == words and saved["texts"] == texts and saved["model"] == model
    )


def _reusable_vectors(saved, model):
    if saved is None or saved["model"] != model:
        return {}
    return {
        (word, text): vector
        for word, text, vector in zip(
            saved["words"], saved["texts"], saved["embeddings"]
        )
    }


def _fetch_embeddings(pairs, model):
    client = OpenAI()
    vectors = {}
    for start in range(0, len(pairs), _EMBEDDING_BATCH):
        batch = pairs[start : start + _EMBEDDING_BATCH]
        response = _create_embeddings(client, model, [text for _, text in batch])
        for item in response.data:
            word, text = batch[item.index]
            vectors[word, text] = numpy.array(item.embedding, dtype=numpy.float32)
        done = min(start + len(batch), len(pairs))
        print(f"Embedded {done}/{len(pairs)}")
    return vectors


def _create_embeddings(client, model, texts):
    delay = 1
    for attempt in range(5):
        try:
            return client.embeddings.create(model=model, input=texts)
        except (APIConnectionError, RateLimitError) as exc:
            if attempt == 4:
                raise
            print(f"Embedding request failed ({exc}); retrying in {delay}s")
            time.sleep(delay)
            delay *= 2
