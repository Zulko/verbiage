from utils import download
import pandas
import json
from pathlib import Path
import yaml

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

with open(dir / "instructions" / "en" / "keep_and_avoid.yaml", "r") as f:
    keep_and_avoid = yaml.load(f, Loader=yaml.FullLoader)


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
with open(Path(__file__).parent / "instructions" / "en" / "en_words.json", "w") as f:
    json.dump(data, f, indent=2)
