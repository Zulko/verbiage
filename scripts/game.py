import click
from functools import wraps
from dotenv import load_dotenv
from VerbiageGame import VerbiageGame
from gemini_batch import gemini_batch
from openai_batch import fetch_completed_batch, openai_batch
import json
from datetime import datetime, timezone
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
        default="gpt-6.1-terra",
        help="AI model to use (default: gpt-6.1-terra)",
    )
    @click.option(
        "--thinking-budget",
        default="low",
        help=(
            "Thinking effort (none, low, medium, high, xhigh, max) "
            "or a Gemini token count (default: low)"
        ),
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

    if word is not None:
        word_size = len(word)

    game = VerbiageGame(language=language, debug=debug)
    game.play(
        word_size=word_size,
        word=word,
        model=model,
        thinking_budget=thinking_budget,
    )


@main.command()
@common_options
def self_play(language, word, model, debug, word_size, thinking_budget):
    """Play the word guessing game."""
    # Create game instance for the specified language

    if word is not None:
        word_size = len(word)

    game = VerbiageGame(language=language, debug=debug)
    game.play(
        word_size=word_size,
        word=word,
        model=model,
        thinking_budget=thinking_budget,
        self_play=True,
    )


@main.command()
@common_options
@click.option(
    "--batched",
    is_flag=True,
    help="Send one multi-clue prompt per secret test word through the normal API",
)
def test(language, word, model, debug, thinking_budget, word_size, batched):
    """Run tests on a series of words."""
    # Create game instance for the specified language
    game = VerbiageGame(language=language, debug=debug)

    runner = game.run_tests_batched if batched else game.run_tests
    runner(model=model, word=word, thinking_budget=thinking_budget)


def _previous_solutions(puzzles_dir, language):
    """Return secret words already used in this language's puzzles."""
    solutions = []
    for gz_file in sorted((puzzles_dir / language).glob(f"{language}_*.json.gz")):
        with gzip.open(gz_file, "rt") as handle:
            puzzle = json.load(handle)
        solution = puzzle.get("solution")
        if isinstance(solution, str) and solution:
            solutions.append(solution)
    return solutions


def _record_calendar_date(calendar_file, language, today):
    """Prepend today to the language calendar once."""
    calendar_data = json.loads(calendar_file.read_text())
    if today in calendar_data[language]:
        return
    calendar_data[language] = [today] + calendar_data[language]
    calendar_file.write_text(json.dumps(calendar_data, indent=2) + "\n")


@main.command()
@common_options
@click.option(
    "--by-cluster",
    is_flag=True,
    help="Send one prompt per semantic cluster instead of one per word",
)
def daily(language, word, model, debug, word_size, thinking_budget, by_cluster):
    """Generate today's puzzle with GPT-6.1 Terra through the OpenAI Batch API.

    Writes verbiage/public/puzzles/<lang>/<lang>_<utc-date>.json.gz and
    records that date in the puzzle calendar. Skips generation when today's
    file is already there.
    """
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    app_dir = Path(__file__).parent.parent / "verbiage"
    puzzles_dir = app_dir / "public" / "puzzles"
    output_file = puzzles_dir / language / f"{language}_{today}.json.gz"

    if output_file.exists():
        print(f"Puzzle already exists: {output_file}")
    else:
        if word is not None:
            word_size = len(word)

        VerbiageGame(language=language, debug=debug).generate_batch(
            word_size=word_size,
            model=model,
            word=word,
            output_file=output_file,
            thinking_budget=thinking_budget,
            batch_function=openai_batch,
            words_to_exclude=_previous_solutions(puzzles_dir, language),
            by_cluster=by_cluster,
        )

    _record_calendar_date(
        app_dir / "src" / "lib" / "puzzleCalendars.json", language, today
    )


@main.command()
@common_options
@click.option(
    "--output-file",
    default=None,
    help="Path to the output file for batch generation",
)
@click.option(
    "--by-cluster",
    is_flag=True,
    help="Send one prompt per semantic cluster instead of one per word",
)
def batch(
    language, word, model, output_file, word_size, thinking_budget, debug, by_cluster
):
    """Run all the playable words through the model."""
    # Create game instance for the specified language
    game = VerbiageGame(language=language, debug=debug)

    if word is not None:
        word_size = len(word)

    if output_file is None:
        output_file = f"batch_{language}_{model}_{word_size}.json"

    batch_function = gemini_batch if model.startswith("gemini") else openai_batch
    game.generate_batch(
        word_size=word_size,
        model=model,
        word=word,
        output_file=output_file,
        thinking_budget=thinking_budget,
        batch_function=batch_function,
        by_cluster=by_cluster,
    )


@main.command()
@click.option("--batch-id", required=True, help="Finished OpenAI batch id")
@click.option(
    "--language",
    default="en",
    type=click.Choice(["en", "fr"]),
    help="Language for the puzzle (default: en)",
)
@click.option("--date", required=True, help="Puzzle date, YYYY-MM-DD")
def recover(batch_id, language, date):
    """Save a finished OpenAI batch as a daily puzzle."""
    app_dir = Path(__file__).parent.parent / "verbiage"
    puzzles_dir = app_dir / "public" / "puzzles"
    output_file = puzzles_dir / language / f"{language}_{date}.json.gz"

    if output_file.exists():
        print(f"Puzzle already exists: {output_file}")
    else:
        results, solution = fetch_completed_batch(batch_id, language=language)
        results["solution"] = solution
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(output_file, "wt") as handle:
            json.dump(results, handle)
        print(f"Wrote {output_file} with {len(results) - 1} clues")

    _record_calendar_date(
        app_dir / "src" / "lib" / "puzzleCalendars.json", language, date
    )


if __name__ == "__main__":
    main()
