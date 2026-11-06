import click
from functools import wraps
from dotenv import load_dotenv
from VerbiageGame import VerbiageGame, print_usage_cost
from gemini_batch import gemini_batch
from openai_batch import fetch_completed_batch, openai_batch, process_completed_batch
import json
from datetime import datetime, timedelta, timezone
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
        python game.py launch-daily-batch --language en
        python game.py process-finished-batch --language en --date 2026-11-02
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
@click.option(
    "--with-advice", is_flag=True, help="Include generated advice in clue prompts"
)
def test(
    language, word, model, debug, thinking_budget, word_size, batched, with_advice
):
    """Run tests on a series of words."""
    # Create game instance for the specified language
    game = VerbiageGame(language=language, debug=debug)

    runner = game.run_tests_batched if batched else game.run_tests
    runner(
        model=model, word=word, thinking_budget=thinking_budget, with_advice=with_advice
    )


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


def _record_calendar_date(calendar_file, language, day):
    """Insert a puzzle date into the language calendar, newest first."""
    calendar_data = json.loads(calendar_file.read_text())
    dates = calendar_data[language]
    if day in dates:
        return
    dates.append(day)
    dates.sort(reverse=True)
    calendar_file.write_text(json.dumps(calendar_data, indent=2) + "\n")


@main.command()
@common_options
@click.option(
    "--by-cluster",
    is_flag=True,
    help="Send one prompt per semantic cluster instead of one per word",
)
@click.option(
    "--date",
    default=None,
    help="Puzzle date, YYYY-MM-DD (default: today, UTC)",
)
def daily(language, word, model, debug, word_size, thinking_budget, by_cluster, date):
    """Generate a daily puzzle with GPT-6.1 Terra through the OpenAI Batch API.

    Writes verbiage/public/puzzles/<lang>/<lang>_<date>.json.gz and
    records that date in the puzzle calendar. Skips generation when that
    file is already there. The date defaults to today in UTC. A new puzzle
    prints the estimated API cost, with batch clues at half the standard rate.
    """
    if date is None:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    else:
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise click.BadParameter("use YYYY-MM-DD") from None
    app_dir = Path(__file__).parent.parent / "verbiage"
    puzzles_dir = app_dir / "public" / "puzzles"
    output_file = puzzles_dir / language / f"{language}_{date}.json.gz"

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
        app_dir / "src" / "lib" / "puzzleCalendars.json", language, date
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
@click.option(
    "--review-quality",
    is_flag=True,
    help="Review clues with extra paid model calls",
)
def batch(
    language,
    word,
    model,
    output_file,
    word_size,
    thinking_budget,
    debug,
    by_cluster,
    review_quality,
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
        review_quality=review_quality,
    )


def batch_queue_path(language, date):
    """Path of the queued batch record for one language and puzzle date."""
    return (
        Path(__file__).parent.parent
        / "verbiage"
        / "batch_queue"
        / language
        / f"{date}.json"
    )


def read_batch_queue(language, date):
    """Return the queued word and batch id, or None when that day has none."""
    path = batch_queue_path(language, date)
    if not path.exists():
        return None
    return json.loads(path.read_text())


def write_batch_queue(language, date, word, batch_id):
    """Record a submitted batch so a later run can finish that puzzle."""
    path = batch_queue_path(language, date)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"word": word, "batch_id": batch_id}, indent=2) + "\n")


def _puzzle_date(date):
    """Return a YYYY-MM-DD puzzle date, or raise a Click error."""
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise click.BadParameter("use YYYY-MM-DD") from None
    return date


def _write_puzzle_file(output_file, results):
    """Write a puzzle mapping as JSON or gzipped JSON."""
    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    if output_file.name.endswith(".json.gz"):
        with gzip.open(output_file, "wt") as handle:
            json.dump(results, handle)
    else:
        with open(output_file, "w") as handle:
            json.dump(results, handle)


@main.command("launch-daily-batch")
@common_options
@click.option(
    "--date",
    default=None,
    help="Puzzle date the batch is for, YYYY-MM-DD (default: tomorrow, UTC)",
)
def launch_daily_batch(language, word, model, debug, word_size, thinking_budget, date):
    """Submit a clustered clue batch and store its id.

    Stops once OpenAI returns a batch id. The puzzle file is written later
    by process-finished-batch. The date defaults to tomorrow UTC. A date
    that already has a queue file or a puzzle file is left unchanged.
    """
    if date is None:
        date = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        date = _puzzle_date(date)

    app_dir = Path(__file__).parent.parent / "verbiage"
    puzzles_dir = app_dir / "public" / "puzzles"
    puzzle_file = puzzles_dir / language / f"{language}_{date}.json.gz"
    queued = read_batch_queue(language, date)
    if queued is not None:
        print(
            f"Batch already queued for {date}: {queued['batch_id']} ({queued['word']})"
        )
        return
    if puzzle_file.exists():
        print(f"Puzzle already exists: {puzzle_file}")
        return

    if word is not None:
        word_size = len(word)
    game = VerbiageGame(language=language, debug=debug)
    usage_log = []
    secret, _display, _avoid, prompts, _members, _clues = game.build_batch_prompts(
        word_size=word_size,
        model=model,
        word=word,
        thinking_budget=thinking_budget,
        words_to_exclude=_previous_solutions(puzzles_dir, language),
        by_cluster=True,
        usage_log=usage_log,
    )
    _results, batch = openai_batch(
        prompts,
        model=model,
        temperature=0.2,
        thinking_budget=thinking_budget,
        wait=False,
    )
    write_batch_queue(language, date, secret, batch.id)
    print(f"Queued {secret} for {date} as {batch.id}")
    print_usage_cost(model, usage_log)


@main.command("process-finished-batch")
@click.argument("batch_id", required=False)
@click.option(
    "--language",
    "--lang",
    default="en",
    type=click.Choice(["en", "fr"]),
    help="Language for the puzzle (default: en)",
)
@click.option(
    "--model",
    default="gpt-6.1-terra",
    help="Model for follow-up clues (default: gpt-6.1-terra)",
)
@click.option(
    "--thinking-budget",
    default="low",
    help=(
        "Thinking effort for follow-up clues "
        "(none, low, medium, high, xhigh, max; default: low)"
    ),
)
@click.option(
    "--date",
    default=None,
    help="Puzzle date, YYYY-MM-DD. Writes the daily puzzle and calendar.",
)
@click.option(
    "--output-file",
    default=None,
    help="Write the puzzle here instead of the dated daily file",
)
@click.option("--debug", is_flag=True, help="Enable debug mode")
@click.option(
    "--review-quality",
    is_flag=True,
    help="Review clues with extra paid model calls",
)
def process_finished_batch(
    batch_id, language, model, thinking_budget, date, output_file, debug, review_quality
):
    """Download a finished batch, fill any missing clues, and print the cost.

    With no batch id, read verbiage/batch_queue/<lang>/<date>.json. Cluster
    responses that omit words are completed with one normal API call, not
    another batch. Batch clues are priced at half the standard rate and the
    follow-up call at the full rate.
    """
    if date is not None:
        date = _puzzle_date(date)
    if batch_id is None:
        if date is None:
            raise click.UsageError("pass a batch id or --date")
        queued = read_batch_queue(language, date)
        if queued is None:
            print(f"No batch queued for {language} {date}")
            return
        batch_id = queued["batch_id"]
        print(f"Queued word for {date}: {queued['word']}")
    if date is None and output_file is None:
        raise click.UsageError("pass --date or --output-file")
    app_dir = Path(__file__).parent.parent / "verbiage"
    puzzles_dir = app_dir / "public" / "puzzles"
    if date is not None and output_file is None:
        output_file = puzzles_dir / language / f"{language}_{date}.json.gz"
    output_file = Path(output_file)

    if output_file.exists():
        print(f"Puzzle already exists: {output_file}")
    else:
        results, solution, usage_log = process_completed_batch(
            batch_id,
            language=language,
            model=model,
            thinking_budget=thinking_budget,
            debug=debug,
            review_quality=review_quality,
        )
        results["solution"] = solution
        _write_puzzle_file(output_file, results)
        print(f"Wrote {output_file} with {len(results) - 1} clues")
        print_usage_cost(model, usage_log)

    if date is not None:
        _record_calendar_date(
            app_dir / "src" / "lib" / "puzzleCalendars.json", language, date
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
