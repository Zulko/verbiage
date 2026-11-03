import gzip
import json
import urllib.request
from pathlib import Path

import pandas
import yaml
from utils import download, embed_words, embeddings_path, playable_words

# Google News word2vec, the 3 million token binary release shipped by gensim.
WORD2VEC_URL = (
    "https://github.com/piskvorky/gensim-data/releases/download/"
    "word2vec-google-news-300/word2vec-google-news-300.gz"
)


def word2vec_vocabulary(path):
    """Lowercased tokens from Google News word2vec.

    The archive is downloaded only until the token list has been written.
    A capitalized entry such as Quirt still counts for quirt.
    """
    path = Path(path)
    if path.exists():
        return set(path.read_text().splitlines())
    archive = path.with_name("word2vec-google-news-300.gz")
    print(f"Downloading {WORD2VEC_URL}")
    request = urllib.request.Request(WORD2VEC_URL, headers={"User-Agent": "verbiage"})
    with urllib.request.urlopen(request) as response, archive.open("wb") as handle:
        while True:
            chunk = response.read(1 << 20)
            if not chunk:
                break
            handle.write(chunk)
    vocabulary = _word2vec_tokens(archive)
    path.write_text("\n".join(sorted(vocabulary)) + "\n")
    archive.unlink()
    print(f"Wrote {len(vocabulary)} word2vec tokens to {path}")
    return vocabulary


def _word2vec_tokens(archive):
    tokens = set()
    with gzip.open(archive, "rb") as handle:
        count, dimensions = handle.readline().split()
        width = int(dimensions) * 4
        pending = b""
        for index in range(int(count)):
            pending = _fill_until(handle, pending, b" ")
            space = pending.index(b" ")
            token = pending[:space].decode("utf-8", "replace")
            tokens.add(token.lower())
            pending = _fill_width(handle, pending[space + 1 :], width)
            if index % 500_000 == 0:
                print(f"  scanned {index:,} word2vec entries")
    return tokens


def _fill_until(handle, pending, marker):
    while marker not in pending:
        chunk = handle.read(1 << 20)
        if not chunk:
            raise EOFError("truncated word2vec file")
        pending += chunk
    return pending


def _fill_width(handle, pending, width):
    while len(pending) < width:
        chunk = handle.read(1 << 20)
        if not chunk:
            raise EOFError("truncated word2vec vector")
        pending += chunk
    return pending[width:]


def _kept_words(words, vocabulary):
    kept = []
    for word in words:
        if word.lower() in vocabulary:
            kept.append(word)
        else:
            print(f"Word2vec filter dropped kept word {word}")
    return kept


def main():
    # DOWNLOAD DATA

    dir = Path(__file__).parent
    lexicon_path = dir / "data" / "count_1w.txt"
    download(
        url="https://norvig.com/ngrams/count_1w.txt",
        filename=lexicon_path,
        replace=False,
    )
    moby_categories_path = dir / "data" / "mobypos.txt"
    download(
        url="https://www.gutenberg.org/files/3203/files/mobypos.txt",
        filename=moby_categories_path,
        replace=False,
    )

    word_categories_path = dir / "data" / "2of12id.json"
    download(
        url="https://raw.githubusercontent.com/felixfischer/categorized-words/refs/heads/master/2of12id.json",
        filename=word_categories_path,
        replace=False,
    )
    wordnet_thesaurus_path = dir / "data" / "en_thesaurus.jsonl"
    download(
        url="https://raw.githubusercontent.com/zaibacu/thesaurus/refs/heads/master/en_thesaurus.jsonl",
        filename=wordnet_thesaurus_path,
        replace=False,
    )

    # CREATE THE SINGULAR NOUNS LIST

    nouns_list = set()
    for line in moby_categories_path.read_text(encoding="mac_roman").splitlines():
        word, categories = line.split("\\")
        if "N" in categories and (word.lower() == word):
            nouns_list.add(word.lower())

    # INTERSECT WITH WORDNET THESAURUS (removes some stray plurals)

    thesaurus_nouns = set()
    for line in wordnet_thesaurus_path.read_text().splitlines():
        entry = json.loads(line)
        if entry["pos"] == "noun":
            thesaurus_nouns.add(entry["word"])
    nouns_list = nouns_list.intersection(thesaurus_nouns)

    # INTERSECT MOBY WITH 2OF12ID
    word_categories = json.loads(word_categories_path.read_text())
    nouns_list = nouns_list.intersection(set(word_categories["N"]))

    # INTERSECT WITH POPULAR FIVERS LIST

    lexicon = pandas.read_csv(
        lexicon_path, sep="\t", header=None, names=["word", "frequency"]
    ).dropna(subset=["word"])
    nouns = lexicon[lexicon.word.isin(nouns_list)]

    # DROP NOUNS WITH NO GOOGLE NEWS WORD2VEC VECTOR

    vocabulary = word2vec_vocabulary(dir / "data" / "word2vec_vocab.txt")
    has_vector = nouns.word.isin(vocabulary)
    list_length = nouns.word.str.len().isin((4, 5, 6)) & ~nouns.word.str.contains("-")
    dropped = sorted(nouns.loc[~has_vector & list_length, "word"])
    nouns = nouns[has_vector]
    print(f"Word2vec filter dropped {len(dropped)}: {', '.join(dropped)}")

    with open(dir / "en" / "keep_and_avoid.yaml", "r") as f:
        keep_and_avoid = yaml.load(f, Loader=yaml.FullLoader)
    keep_and_avoid["keep_playable"] = _kept_words(
        keep_and_avoid["keep_playable"], vocabulary
    )
    keep_and_avoid["keep_drawable"] = _kept_words(
        keep_and_avoid["keep_drawable"], vocabulary
    )

    def get_words(size):
        subset = nouns[(nouns.word.str.len() == size) & (~nouns.word.str.contains("-"))]
        playable = subset.word.str.upper().to_list()
        drawable = subset[subset.frequency > 5_000_000].word.str.upper().to_list()
        keep_playable = [w for w in keep_and_avoid["keep_playable"] if len(w) == size]
        keep_drawable = [w for w in keep_and_avoid["keep_drawable"] if len(w) == size]
        filtered_drawable = [
            w for w in drawable if w not in keep_and_avoid["avoid_drawable"]
        ]
        playable = sorted(set(playable + keep_playable))
        drawable = sorted(set(filtered_drawable + keep_drawable))
        print(f"{len(playable)} playable, {len(drawable)} drawable of size {size}")
        return {"playable": playable, "drawable": drawable}

    data = {n: get_words(n) for n in [4, 5, 6]}
    with open(dir / "en" / "en_words.json", "w") as f:
        json.dump(data, f, indent=2)
    embed_words(playable_words(data), embeddings_path("en"))


if __name__ == "__main__":
    main()
