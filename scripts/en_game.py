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
random_topics = ", ".join([choice(words["common_nouns"]) for _ in range(5)])

print("Generating character...")


class Character(BaseModel):
    name: str
    description: str
    interests: str
    tone: str


character_prompt = format_template(
    prompts_path / "character.md", word=word, random_topics=random_topics
)
character = run_gemini(
    character_prompt, response_model=Character, temperature=0.9, model=MODEL
)

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
    **character.model_dump(),
    secret_word=word,
    avoid=", ".join(things_to_avoid.avoid),
    advice=things_to_avoid.advice,
)


def play():
    print("🎮 Let's play!")
    print(f"🎭 Today's host is {character.name}. {character.description}")
    while True:
        player_word = input("💭 Your guess >>> ")
        if player_word == "quit":
            print("🏁 The solution was:", word)
            break
        if len(player_word) != 5:
            print("⚠️  Enter a 5-letter word")
            continue
        print("🔍 Checking...")
        response = run_gemini(
            word_response_prompt.replace("{{player_word}}", player_word),
            temperature=0.2,
            model=MODEL,
        )
        print(f"\n🗣️ {response}\n")
        if player_word == word:
            print("🎉 You win! 🏆")
            break


def generate_all_answers():
    """Generate all possible answers for the secret word"""
    prompts = [
        word_response_prompt.replace("{{player_word}}", player_word)
        for player_word in words["drawable"]
    ]


if __name__ == "__main__":
    play()
