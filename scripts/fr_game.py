import click
from dotenv import load_dotenv
from utils import VerbiageGame
from gemini_batch import gemini_batch

# Useful to attribute special keys to this project
load_dotenv()


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
        python fr_game.py --word-size 5 --batch --output-file batch_gemini_5.json
        python fr_game.py --word-size 5 --batch --output-file batch_gemini_5.json --debug
        python fr_game.py --word-size 5 --test --debug
        python fr_game.py --word-size 5 --debug
        python fr_game.py --word-size 5
        python fr_game.py --test
        python fr_game.py --test --word POPE
        python fr_game.py --batch --word-size 5  --output-file batch_gemini_5.json
        python fr_game.py --batch --word POPE  --output-file batch_gemini_5.json
    """
    # Create French game instance
    game = VerbiageGame(language="fr")

    if word is not None:
        word_size = len(word)

    if test:
        game.run_tests(
            model=model, debug=debug, word=word, thinking_budget=thinking_budget
        )
    elif batch:
        if output_file is None:
            output_file = f"batch_{model}_{word_size}.json"
        game.generate_batch(
            word_size=word_size,
            model=model,
            word=word,
            output_file=output_file,
            thinking_budget=thinking_budget,
            batch_function=gemini_batch,
        )
    else:
        game.play(
            word_size=word_size,
            debug=debug,
            word=word,
            model=model,
            thinking_budget=thinking_budget,
        )


if __name__ == "__main__":
    main()
