from utils import download
import pandas
import json
from pathlib import Path

# DOWNLOAD DATA

lexicon_path = Path("data") / "count_1w.txt"
download(
    url="https://norvig.com/ngrams/count_1w.txt",
    filename=lexicon_path,
    replace=False,
)
moby_categories_path = Path(__file__).parent / "data" / "mobypos.txt"
download(
    url="https://www.gutenberg.org/files/3203/files/mobypos.txt",
    filename=moby_categories_path,
    replace=False,
)

word_categories_path = Path(__file__).parent / "data" / "2of12id.json"
download(
    url="https://raw.githubusercontent.com/felixfischer/categorized-words/refs/heads/master/2of12id.json",
    filename=word_categories_path,
    replace=False,
)
wordnet_thesaurus_path = Path(__file__).parent / "data" / "en_thesaurus.jsonl"
download(
    url="https://raw.githubusercontent.com/zaibacu/thesaurus/refs/heads/master/en_thesaurus.jsonl",
    filename=wordnet_thesaurus_path,
    replace=False,
)


# CREATE THE SINGULAR NOUNS LIST

nouns_list = set()
for line in moby_categories_path.read_text(encoding="mac_roman").splitlines():
    word, categories = line.split("\\")
    if "N" in categories and "A" not in categories and (word.lower() == word):
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
fivers = nouns[(nouns.word.str.len() == 5) & (~nouns.word.str.contains("-"))]
playable = fivers.word.str.upper().to_list()
drawable = fivers[fivers.frequency > 5_000_000].word.str.upper().to_list()
print(f"{len(playable)} playable, {len(drawable)} drawable")
data = {"playable": playable, "drawable": drawable}
with open(Path(__file__).parent / "instructions" / "en" / "en_fivers.json", "w") as f:
    json.dump(data, f, indent=2)
