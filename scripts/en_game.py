from pathlib import Path
import json
from random import choice
from pydantic import BaseModel
from utils import run_gemini, format_template

MODEL = "gemini-2.5-flash"
prompts_path = Path(__file__).parent / "instructions" / "en"

print("Picking a word...")
words_path = prompts_path / "en_fivers.json"
words = json.loads(words_path.read_text())
word = choice(words["drawable"])

print("Generating advice on things to avoid...")


class ThingsToAvoid(BaseModel):
    avoid: list[str]
    advice: str


things_to_avoid_prompt = format_template(prompts_path / "things_to_avoid.md", word=word)
things_to_avoid = run_gemini(
    things_to_avoid_prompt, response_model=ThingsToAvoid, temperature=0.4, model=MODEL
)

word_response_prompt = format_template(
    prompts_path / "word_response.md",
    secret_word=word,
    avoid=", ".join(things_to_avoid.avoid),
    advice=things_to_avoid.advice,
)


def play(debug=False):
    print("🎮 Let's play!")
    if debug:
        print(f"🔍 The secret word is {word}")
    while True:
        player_word = input("💭 Your guess >>> ")
        if player_word == "quit":
            print("🏁 The solution was:", word)
            break
        if player_word.upper() not in words["playable"]:
            print(f"⚠️  {player_word.upper()} is not in my list")
            continue
        print("🔍 Checking...")
        response = run_gemini(
            word_response_prompt.replace("{{player_word}}", player_word),
            temperature=0.2,
            model=MODEL,
            debug=debug,
        )
        print(f"\n🗣️ {response}\n")
        if player_word == word:
            print("🎉 You win! 🏆")
            break


if __name__ == "__main__":
    play(debug=True)
