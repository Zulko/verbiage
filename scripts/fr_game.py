from pathlib import Path
import json
import time
from random import choice
from pydantic import BaseModel
from dotenv import load_dotenv
import click
from utils import format_template, run_gemini, run_openai
from gemini_batch import gemini_batch
import gzip

# Useful to attribute special keys to this project
load_dotenv()

prompts_path = Path(__file__).parent / "instructions" / "fr"
words_path = prompts_path / "fr_words.json"


def get_client(model):
    if model.startswith("gemini"):
        return run_gemini
    return run_openai


def get_random_word(words):
    return choice(words["drawable"])


def generate_things_to_avoid(word, model):
    class MotsAEviter(BaseModel):
        mots_interdits: list[str]
        conseils: str

    things_to_avoid_prompt = format_template(
        prompts_path / "things_to_avoid.md", word=word
    )
    client = get_client(model)
    return client(
        things_to_avoid_prompt,
        response_model=MotsAEviter,
        temperature=0.4,
        model=model,
        thinking_budget=None,
    )


def play(
    words,
    accented_dict,
    debug=False,
    word=None,
    things_to_avoid=None,
    model="gemini-2.5-flash",
    thinking_budget=None,
):
    if word is None:
        word = get_random_word(words)
    else:
        print(f"Mot secret: {word}")

    print("Génération des conseils sur les mots à éviter...")
    word_with_accents = accented_dict.get(word, word)
    things_to_avoid = generate_things_to_avoid(word_with_accents, model)

    client = get_client(model)
    word_response_prompt = format_template(
        prompts_path / "word_response.md",
        secret_word=word_with_accents,
        avoid=", ".join(things_to_avoid.mots_interdits),
        advice=things_to_avoid.conseils,
    )
    print("🎮 C'est parti!")
    if debug:
        print(f"🔍 Le mot secret est {word}")
        print(f"🔍 Les mots à éviter sont {things_to_avoid.mots_interdits}")
    while True:
        player_word = input("💭 Votre mot >>> ").upper()
        if player_word == "QUIT":
            print("🏁 Le mot secret était:", word)
            break
        if len(player_word) == 0:
            continue
        if len(player_word) != len(word):
            print(f"⚠️  Entrez un mot de {len(word)} lettres")
            continue

        if player_word not in words["playable"]:
            print(f"⚠️  {player_word} n'est pas dans ma liste")
            continue
        if player_word == word:
            print("🎉 Vous avez gagné! 🏆")
            break
        print("🔍 Vérification...")
        player_word_with_accents = accented_dict.get(player_word, player_word)
        response = client(
            word_response_prompt.replace("{{player_word}}", player_word_with_accents),
            temperature=0.2,
            model=model,
            debug=debug,
            thinking_budget=thinking_budget,
        )
        print(f"\n🗣️ {response}\n")


def run_tests(model, debug, word, accented_dict, thinking_budget=None):
    test_words = json.loads((prompts_path / "test_words.json").read_text())
    client = get_client(model)

    if word is not None:
        test_words = {word: test_words[word]}

    for word, guesses in test_words.items():
        print(f"LE MOT est {word}")
        accented_word = accented_dict.get(word, word)
        things_to_avoid = generate_things_to_avoid(accented_word, model)
        word_response_prompt = format_template(
            prompts_path / "word_response.md",
            secret_word=accented_word,
            avoid=", ".join(things_to_avoid.mots_interdits),
            advice=things_to_avoid.conseils,
        )
        for guess in guesses:
            guess_with_accents = accented_dict.get(guess, guess)
            response = client(
                word_response_prompt.replace("{{player_word}}", guess_with_accents),
                temperature=0.2,
                model=model,
                debug=debug,
                thinking_budget=thinking_budget,
            )
            print(response)


def generate_batch(
    accented_dict, words, model, word, output_file, thinking_budget=None
):
    start_time = time.time()
    if word is None:
        print("Picking a random word...")
        word = get_random_word(words)

    print("Generating words to avoid")
    word_with_accents = accented_dict.get(word, word)
    things_to_avoid = generate_things_to_avoid(word_with_accents, model)

    print("Generating word responses")
    word_response_prompt = format_template(
        prompts_path / "word_response.md",
        secret_word=word_with_accents,
        avoid=", ".join(things_to_avoid.mots_interdits),
        advice=things_to_avoid.conseils,
    )
    prompts_by_word = {
        word: word_response_prompt.replace(
            "{{player_word}}", accented_dict.get(word, word)
        )
        for word in words["playable"]
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
    results["solution"] = word

    print(f"Writing to file {output_file}")
    if output_file.endswith(".json.gz"):
        with gzip.open(output_file, "wt") as f:
            json.dump(results, f)
    else:
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
    default=None,
    help="Budget for thinking in tokens (default: None)",
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
        run_tests(
            model=model,
            debug=debug,
            word=word,
            thinking_budget=thinking_budget,
            accented_dict=all_words["accented_dict"],
        )
    elif batch:
        if output_file is None:
            output_file = f"batch_{model}_{word_size}.json"
        generate_batch(
            words=words,
            accented_dict=all_words["accented_dict"],
            model=model,
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
            accented_dict=all_words["accented_dict"],
        )


if __name__ == "__main__":
    main()
