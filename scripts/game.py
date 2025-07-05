import click
from dotenv import load_dotenv
from VerbiageGame import VerbiageGame
from gemini_batch import gemini_batch

# Useful to attribute special keys to this project
load_dotenv()


@click.command()
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
def main(
    language, word, model, debug, word_size, test, batch, output_file, thinking_budget
):
    """Play the word guessing game in English or French.

    Examples:
        python game.py --language en --word-size 5
        python game.py --language fr --word-size 5 --debug
        python game.py --language en --test --word POPE
        python game.py --language fr --test --word PAPE
        python game.py --language en --batch --word-size 5 --output-file batch_en_5.json
        python game.py --language fr --batch --word-size 5 --output-file batch_fr_5.json
        python game.py --language en --batch --word POPE --output-file batch_en_pope.json
        python game.py --language fr --batch --word PAPE --output-file batch_fr_pape.json
    """
    # Create game instance for the specified language
    game = VerbiageGame(language=language)

    if word is not None:
        word_size = len(word)

    if test:
        game.run_tests(
            model=model, debug=debug, word=word, thinking_budget=thinking_budget
        )
    elif batch:
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
