import click
from functools import wraps
from dotenv import load_dotenv
from VerbiageGame import VerbiageGame
from gemini_batch import gemini_batch
import json
from datetime import datetime
from pathlib import Path
import gzip

# Useful to attribute special keys to this project
load_dotenv()


def common_options(f):
    """Common options shared across all commands."""

    @click.option(
        "--language",
        default="en",
        type=click.Choice(["en", "fr"]),
        help="Language for the game (default: en)",
    )
    @click.option("--word", help="Force a specific word for the game")
    @click.option(
        "--model",
        default="gemini-2.5-flash",
        help="AI model to use (default: gemini-2.5-flash)",
    )
    @click.option(
        "--thinking-budget",
        default=None,
        help="Budget for thinking in tokens (default: None)",
    )
    @click.option(
        "--debug", is_flag=True, help="Enable debug mode to show the secret word"
    )
    @click.option(
        "--word-size",
        default=5,
        help="Size of the words to play with (default: 5)",
    )
    @wraps(f)
    def wrapper(*args, **kwargs):
        return f(*args, **kwargs)

    return wrapper


@click.group()
def main():
    """Play the word guessing game in English or French.

    Examples:
        python game.py play --language en --word-size 5
        python game.py test --language fr --word POPE
        python game.py daily-puzzle --word-size 5
        python game.py batch --language en --word-size 5 --output-file batch_en_5.json
    """
    pass


@main.command()
@common_options
def play(language, word, model, debug, word_size, thinking_budget):
    """Play the word guessing game."""
    # Create game instance for the specified language
    game = VerbiageGame(language=language, debug=debug)
    print(debug)

    if word is not None:
        word_size = len(word)

    game.play(
        word_size=word_size,
        word=word,
        model=model,
        thinking_budget=thinking_budget,
    )


@main.command()
@common_options
def test(language, word, model, debug, thinking_budget, word_size):
    """Run tests on a series of words."""
    # Create game instance for the specified language
    game = VerbiageGame(language=language, debug=debug)

    game.run_tests(model=model, word=word, thinking_budget=thinking_budget)


@main.command()
@common_options
def daily(language, word, model, debug, word_size, thinking_budget):
    """Automatically generate a daily word."""
    # Create game instance for the specified language
    today = datetime.now().strftime("%Y-%m-%d")
    app_dir = Path(__file__).parent.parent / "verbiage"
    puzzles_dir = app_dir / "public" / "puzzles"
    output_file = puzzles_dir / language / f"{language}_{today}.json.gz"
    game = VerbiageGame(language=language, debug=debug)

    if word is not None:
        word_size = len(word)

    words_to_exclude = []
    for gz_file in puzzles_dir.glob(f"{language}*.json.gz"):
        with gzip.open(gz_file, "rt") as f:
            words_to_exclude.extend(json.load(f)["solution"])

    game.generate_batch(
        word_size=word_size,
        model=model,
        word=word,
        output_file=output_file,
        thinking_budget=thinking_budget,
        batch_function=gemini_batch,
        words_to_exclude=words_to_exclude,
        max_words=10,
    )
    # Update puzzleCalendar.json
    calendar_file = app_dir / "src" / "lib" / "puzzleCalendars.json"
    calendar_data = json.loads(calendar_file.read_text())
    calendar_data[language] = [today] + calendar_data[language]
    calendar_file.write_text(json.dumps(calendar_data, indent=2))


@main.command()
@common_options
@click.option(
    "--output-file",
    default=None,
    help="Path to the output file for batch generation",
)
def batch(language, word, model, output_file, word_size, thinking_budget, debug):
    """Run all the playable words through the model."""
    # Create game instance for the specified language
    game = VerbiageGame(language=language, debug=debug)

    if word is not None:
        word_size = len(word)

    if output_file is None:
        output_file = f"batch_{language}_{model}_{word_size}.json"

    game.generate_batch(
        word_size=word_size,
        model=model,
        word=word,
        output_file=output_file,
        thinking_budget=thinking_budget,
        batch_function=gemini_batch,
    )


if __name__ == "__main__":
    main()
