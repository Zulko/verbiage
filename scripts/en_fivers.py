from utils import download
import pandas
import json
from pathlib import Path

lexicon_path = Path("data") / "count_1w.txt"
download(
    url="https://norvig.com/ngrams/count_1w.txt",
    filename=lexicon_path,
    replace=False,
)
word_categories_path = Path(__file__).parent / "data" / "2of12id.json"
download(
    url="https://raw.githubusercontent.com/felixfischer/categorized-words/refs/heads/master/2of12id.json",
    filename=word_categories_path,
    replace=False,
)
word_categories = json.loads(word_categories_path.read_text())
nouns_list = set(word_categories["N"])

lexicon = pandas.read_csv(
    lexicon_path, sep="\t", header=None, names=["word", "frequency"]
).dropna(subset=["word"])
nouns = lexicon[lexicon.word.isin(nouns_list)]
fivers = nouns[(nouns.word.str.len() == 5) & (~nouns.word.str.contains("-"))]
playable = fivers.word.str.upper().to_list()
drawable = fivers[fivers.frequency > 800_000].word.str.upper().to_list()
print(f"{len(playable)} playable, {len(drawable)} drawable")
data = {"playable": playable, "drawable": drawable}
with open(Path(__file__).parent / "instructions" / "en" / "en_fivers.json", "w") as f:
    json.dump(data, f)
