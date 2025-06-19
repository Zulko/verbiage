from utils import download
import pandas
import json
import re
from pathlib import Path

lexicon_path = Path(__file__).parent / "data" / "Lexique383.tsv"
download(
    url="http://www.lexique.org/databases/Lexique383/Lexique383.tsv",
    filename=lexicon_path,
    replace=False,
)
lexicon = pandas.read_csv(lexicon_path, sep="\t").dropna(subset=["ortho"])
fivers = lexicon[(lexicon.ortho.str.len() == 5) & (~lexicon.ortho.str.contains("-"))]
# not_a_verb = (fivers.cgramortho != "VER") & (fivers.cgramortho != "AUX,VER")
# not_conjugated = fivers.lemme == fivers.ortho
# unconjugated = fivers[not_a_verb | not_conjugated]
nouns = fivers[fivers.cgram == "NOM"]


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


unaccented_dict = {word: replace_accents(word).upper() for word in nouns.ortho}
accented_dict = {unaccented: word for word, unaccented in unaccented_dict.items()}
playable = [unaccented_dict[word] for word in nouns.ortho]
not_rare = nouns[(nouns.freqfilms2 > 0) & (nouns.freqlivres > 0)]
drawable = [unaccented_dict[word] for word in not_rare.ortho]
print(f"Found {len(drawable)} drawable words, {len(playable)} playable words")
data = {"drawable": drawable, "playable": playable, "accented_dict": accented_dict}
with open(Path(__file__).parent / "fr_fivers.json", "w") as f:
    json.dump(data, f)
