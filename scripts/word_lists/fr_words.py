from utils import download
from pathlib import Path
import pandas
import json
import re


def replace_accents(word):
    """Replace all accented characters with their unaccented version"""
    replacements = {
        r"[àâä]": "a",
        r"[éèêë]": "e",
        r"[îï]": "i",
        r"[ôö]": "o",
        r"[ûü]": "u",
        r"[ç]": "c",
        r"[œ]": "oe",
        r"[æ]": "ae",
    }

    for pattern, replacement in replacements.items():
        word = re.sub(pattern, replacement, word)
    return word


dir = Path(__file__).parent
lexicon_path = dir / "data" / "Lexique383.tsv"
download(
    url="http://www.lexique.org/databases/Lexique383/Lexique383.tsv",
    filename=lexicon_path,
    replace=False,
)
lexicon = pandas.read_csv(lexicon_path, sep="\t").dropna(subset=["ortho"])
nouns = lexicon[
    (lexicon.cgram == "NOM")
    & (lexicon.nombre != "p")
    & (lexicon.deflem > 40)
    & (lexicon.freqfilms2 > 0)
    & (lexicon.freqlivres > 0)
]
print("found", len(nouns), "singular nouns")

adjectives = set(
    [replace_accents(word).upper() for word in lexicon[(lexicon.cgram == "ADJ")].ortho]
)
print("found", len(adjectives), "adjectives")

unaccented_words = set(
    [word.upper() for word in nouns.ortho if replace_accents(word) == word]
)

unaccented_dict = {word.upper(): replace_accents(word).upper() for word in nouns.ortho}
accented_dict = {
    unaccented: word
    for word, unaccented in unaccented_dict.items()
    if unaccented != word and unaccented not in unaccented_words
}


def get_words(size):
    sized_nouns = nouns[
        (nouns.ortho.str.len() == size) & (~nouns.ortho.str.contains("-"))
    ]
    known_nouns = sized_nouns[(sized_nouns.deflem > 80) & (sized_nouns.freqfilms2 > 5)]
    playable = [unaccented_dict[word.upper()] for word in sized_nouns.ortho]
    drawable = [
        unaccented_dict[word.upper()]
        for word in known_nouns.ortho
        if word not in adjectives
    ]
    print(f"{len(playable)} playable, {len(drawable)} drawable of size {size}")
    return {"drawable": drawable, "playable": playable}


data = {n: get_words(n) for n in [4, 5, 6]}
all_words = set(word for subdata in data.values() for word in subdata["drawable"])
data["accented_dict"] = {k: v for k, v in accented_dict.items() if k in all_words}
with open(dir / "fr" / "fr_words.json", "w") as f:
    json.dump(data, f, indent=2)
with open(dir.parent / "verbiage" / "public" / "fr_accented_dict.json", "w") as f:
    json.dump(accented_dict, f, indent=2)
