from pathlib import Path
import json
import time
from random import choice
from pydantic import BaseModel
from dotenv import load_dotenv
import click
from utils import format_template, run_gemini, run_openai
from gemini_batch import gemini_batch

# Useful to attribute special keys to this project
load_dotenv()

prompts_path = Path(__file__).parent / "instructions" / "en"
words_path = prompts_path / "en_words.json"


def get_client(model):
    return run_gemini if model.startswith("gemini") else run_openai


def get_random_word(words):
    print("Picking a word...")

    return choice(words["drawable"])


def generate_things_to_avoid(word, model):
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
        thinking_budget=3000,
    )


def play(
    words,
    debug=False,
    word=None,
    things_to_avoid=None,
    model="gemini-2.5-flash",
    thinking_budget=0,
):
    if word is None:
        word = get_random_word(words)
    else:
        print(f"Using provided word: {word}")

    print("Generating advice on things to avoid...")
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
        if len(player_word) == 0:
            continue
        if len(player_word) != len(word):
            print(f"⚠️  Please enter a {len(word)}-letter word")
            continue

        if player_word.upper() not in words["playable"]:
            print(f"⚠️  {player_word.upper()} is not in my list")
            continue
        if player_word.upper() == word:
            print("🎉 You win! 🏆")
            break
        print("🔍 Checking...")
        response = client(
            word_response_prompt.replace("{{player_word}}", player_word),
            temperature=0.2,
            model=model,
            debug=debug,
            thinking_budget=thinking_budget,
        )
        print(f"\n🗣️ {response}\n")


def run_tests(model, debug, word, thinking_budget=0):
    test_words = json.loads((prompts_path / "test_words.json").read_text())
    client = get_client(model)

    if word is not None:
        test_words = {word: test_words[word]}

    for word, guesses in test_words.items():
        print(f"\nTHE WORD is {word}")
        things_to_avoid = generate_things_to_avoid(word, model)
        word_response_prompt = format_template(
            prompts_path / "word_response.md",
            secret_word=word,
            avoid=", ".join(things_to_avoid.avoid),
            advice=things_to_avoid.advice,
        )
        for guess in guesses:
            response = client(
                word_response_prompt.replace("{{player_word}}", guess),
                temperature=0.2,
                model=model,
                debug=debug,
                thinking_budget=thinking_budget,
            )
            print(response)


def generate_batch(words, model, debug, word, output_file, thinking_budget=0):
    start_time = time.time()
    if word is None:
        print("Picking a random word...")
        word = get_random_word(words)

    print("Generating words to avoid")
    things_to_avoid = generate_things_to_avoid(word, model)

    print("Generating word responses")
    word_response_prompt = format_template(
        prompts_path / "word_response.md",
        secret_word=word,
        avoid=", ".join(things_to_avoid.avoid),
        advice=things_to_avoid.advice,
    )
    prompts_by_word = {
        word: word_response_prompt.replace("{{player_word}}", word)
        for word in words["playable"][:10]
    }
    results, _job = gemini_batch(
        prompts_by_word,
        model=model,
        temperature=0.2,
        gcs_bucket="verbiage-files",
        project_id="gen-lang-client-0608167298",
        location="us-central1",
        thinking_budget=thinking_budget,
    )
    results["the_word"] = word

    print(f"Writing to file {output_file}")
    with open(output_file, "w") as f:
        json.dump(results, f)
    print(f"Done in {int(time.time() - start_time)} seconds")


@click.command()
@click.option("--word", help="Force a specific word for the game")
@click.option(
    "--model",
    default="gemini-2.5-flash",
    help="AI model to use (default: gemini-2.5-flash)",
)
@click.option("--debug", is_flag=True, help="Enable debug mode to show the secret word")
@click.option("--test", help="Run tests on a series of words", is_flag=True)
@click.option(
    "--batch",
    help="Run all the playable words through the model",
    is_flag=True,
)
@click.option(
    "--output-file", default=None, help="Path to the output file for batch generation"
)
@click.option(
    "--word-size",
    default=5,
    help="Size of the words to play with (default: 5)",
)
@click.option(
    "--thinking-budget",
    default=0,
    help="Budget for thinking in tokens (default: 0)",
)
def main(word, model, debug, word_size, test, batch, output_file, thinking_budget):
    """Play the word guessing game.

    Examples:
        python en_game.py --word-size 5 --batch --output-file batch_gemini_5.json
        python en_game.py --word-size 5 --batch --output-file batch_gemini_5.json --debug
        python en_game.py --word-size 5 --test --debug
        python en_game.py --word-size 5 --debug
        python en_game.py --word-size 5
        python en_game.py --test
        python en_game.py --test --word POPE
        python en_game.py --batch --word-size 5  --output-file batch_gemini_5.json
        python en_game.py --batch --word POPE  --output-file batch_gemini_5.json
    """
    all_words = json.loads(words_path.read_text())
    if word is not None:
        word_size = len(word)
    words = all_words[str(word_size)]
    if test:
        run_tests(model=model, debug=debug, word=word, thinking_budget=thinking_budget)
    elif batch:
        if output_file is None:
            output_file = f"batch_{model}_{word_size}.json"
        generate_batch(
            words=words,
            model=model,
            debug=debug,
            word=word,
            output_file=output_file,
            thinking_budget=thinking_budget,
        )
    else:
        play(
            words=words,
            debug=debug,
            word=word,
            model=model,
            thinking_budget=thinking_budget,
        )


if __name__ == "__main__":
    main()
