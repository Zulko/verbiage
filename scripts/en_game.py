from pathlib import Path
import json
from random import choice
from pydantic import BaseModel
from dotenv import load_dotenv
import click
from utils import format_template, run_gemini, run_openai

# Useful to attribute special keys to this project
load_dotenv()

prompts_path = Path(__file__).parent / "instructions" / "en"
words_path = prompts_path / "en_fivers.json"
words = json.loads(words_path.read_text())


def get_client(model):
    return run_gemini if model.startswith("gemini") else run_openai


def get_random_word():
    print("Picking a word...")

    return choice(words["drawable"])


def generate_things_to_avoid(word, model):
    print("Generating advice on things to avoid...")

    class ThingsToAvoid(BaseModel):
        avoid: list[str]
        advice: str

    things_to_avoid_prompt = format_template(
        prompts_path / "things_to_avoid.md", word=word
    )
    client = get_client(model)
    return client(
        things_to_avoid_prompt,
        response_model=ThingsToAvoid,
        temperature=0.4,
        model=model,
    )


def play(debug=False, word=None, things_to_avoid=None, model="gemini-2.5-flash"):
    if word is None:
        word = get_random_word()
    else:
        print(f"Using provided word: {word}")

    things_to_avoid = generate_things_to_avoid(word, model)
    client = get_client(model)
    word_response_prompt = format_template(
        prompts_path / "word_response.md",
        secret_word=word,
        avoid=", ".join(things_to_avoid.avoid),
        advice=things_to_avoid.advice,
    )
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
        response = client(
            word_response_prompt.replace("{{player_word}}", player_word),
            temperature=0.2,
            model=model,
            debug=debug,
        )
        print(f"\n🗣️ {response}\n")
        if player_word == word:
            print("🎉 You win! 🏆")
            break


@click.command()
@click.option("--word", help="Force a specific word for the game")
@click.option(
    "--model",
    default="gemini-2.5-flash",
    help="AI model to use (default: gemini-2.5-flash)",
)
@click.option("--debug", is_flag=True, help="Enable debug mode to show the secret word")
def main(word, model, debug):
    """Play the word guessing game."""
    play(debug=debug, word=word, model=model)


if __name__ == "__main__":
    main()
