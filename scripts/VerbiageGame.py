from pathlib import Path
import requests
from typing import Optional
from pydantic import BaseModel
from google import genai
from openai import OpenAI
import json
import time
import gzip
from random import choice


def run_gemini(
    prompt,
    model="gemini-2.5-flash",
    response_model: Optional[BaseModel] = None,
    temperature: float = 0.0,
    debug: bool = False,
    thinking_budget: int = None,
) -> BaseModel | str:
    """Get a response from the Gemini API"""
    client = genai.Client()
    params = {"temperature": temperature}
    if thinking_budget is not None:
        tk_config = genai.types.ThinkingConfig(thinking_budget=thinking_budget)
        params["thinking_config"] = tk_config
    if response_model is not None:
        config = genai.types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=response_model.model_json_schema(),
            **params,
        )
    else:
        config = genai.types.GenerateContentConfig(
            response_mime_type="text/plain", **params
        )
    resp = client.models.generate_content(model=model, contents=prompt, config=config)
    usage = resp.usage_metadata
    if debug:
        print(
            f"Tokens: {usage.prompt_token_count} in, "
            f"{usage.candidates_token_count} out, "
            f"{usage.thoughts_token_count} thoughts"
        )
    text = resp.candidates[0].content.parts[0].text
    if response_model is not None:
        return response_model.model_validate_json(text)
    else:
        return text


def run_openai(
    prompt,
    model="gpt-4o-mini",
    response_model: Optional[BaseModel] = None,
    temperature: float = 0.0,
    debug: bool = False,
    thinking_budget: int = None,
) -> BaseModel | str:
    """Get a response from the OpenAI API"""
    client = OpenAI()

    messages = [{"role": "user", "content": prompt}]

    if response_model is not None:
        # Use structured output with response_format
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": response_model.__name__,
                    "schema": response_model.model_json_schema(),
                },
            },
        )
    else:
        # Standard text completion
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
        )

    if debug:
        usage = completion.usage
        print(f"Tokens: {usage.prompt_tokens} in, {usage.completion_tokens} out")

    text = completion.choices[0].message.content

    if response_model is not None:
        return response_model.model_validate_json(text)
    else:
        return text


def format_template(template_path: Path, **kwargs):
    """Format a template with the given kwargs"""
    template = template_path.read_text()
    for key, value in kwargs.items():
        template = template.replace(f"{{{{{key}}}}}", value)
    return template


class VerbiageGame:
    """
    A unified game class that handles both English and French word guessing games.
    """

    def __init__(self, language: str = "en", debug: bool = False):
        """
        Initialize the game with the specified language.

        Args:
            language: "en" for English or "fr" for French
        """
        if language not in ["en", "fr"]:
            raise ValueError("Language must be 'en' or 'fr'")

        self.language = language
        self.prompts_path = Path(__file__).parent / "instructions" / language
        self.words_path = self.prompts_path / f"{language}_words.json"

        # Load words data
        self.all_words = json.loads(self.words_path.read_text())

        # Language-specific configurations
        self._setup_language_config()
        self.debug = debug

    def debug_print(self, message):
        """Print a message if debug is enabled."""
        if self.debug:
            print(message)

    def _setup_language_config(self):
        """Setup language-specific configurations."""
        if self.language == "en":
            self.config = {
                "response_model_class": self._create_english_response_model(),
                "avoid_field": "avoid",
                "advice_field": "advice",
                "messages": {
                    "picking_word": "Picking a word...",
                    "using_word": "Using provided word: {}",
                    "generating_advice": "Generating advice on things to avoid...",
                    "lets_play": "🎮 Let's play!",
                    "secret_word": "🔍 The secret word is {}",
                    "input_prompt": "💭 Your guess >>> ",
                    "quit_command": "quit",
                    "quit_message": "🏁 The solution was: {}",
                    "length_warning": "⚠️  Please enter a {}-letter word",
                    "not_in_list": "⚠️  {} is not in my list",
                    "win_message": "🎉 You win! 🏆",
                    "checking": "🔍 Checking...",
                    "test_word_prefix": "THE WORD is {}",
                },
                "has_accents": False,
                "case_conversion": lambda x: x.upper(),
            }
        else:  # French
            self.config = {
                "response_model_class": self._create_french_response_model(),
                "avoid_field": "mots_interdits",
                "advice_field": "conseils",
                "messages": {
                    "picking_word": "Picking a word...",
                    "using_word": "Mot secret: {}",
                    "generating_advice": "Génération des conseils sur les mots à éviter...",
                    "lets_play": "🎮 C'est parti!",
                    "secret_word": "🔍 Le mot secret est {}",
                    "input_prompt": "💭 Votre mot >>> ",
                    "quit_command": "QUIT",
                    "quit_message": "🏁 Le mot secret était: {}",
                    "length_warning": "⚠️  Entrez un mot de {} lettres",
                    "not_in_list": "⚠️  {} n'est pas dans ma liste",
                    "win_message": "🎉 Vous avez gagné! 🏆",
                    "checking": "🔍 Vérification...",
                    "test_word_prefix": "LE MOT est {}",
                },
                "has_accents": True,
                "case_conversion": lambda x: x.upper(),
            }

    def _create_english_response_model(self):
        """Create the English response model."""

        class ThingsToAvoid(BaseModel):
            avoid: list[str]
            advice: str

        return ThingsToAvoid

    def _create_french_response_model(self):
        """Create the French response model."""

        class MotsAEviter(BaseModel):
            mots_interdits: list[str]
            conseils: str

        return MotsAEviter

    def get_client(self, model):
        """Get the appropriate AI client based on the model."""
        return run_gemini if model.startswith("gemini") else run_openai

    def get_random_word(self, words):
        """Get a random word from the drawable words."""
        print(self.config["messages"]["picking_word"])
        return choice(words["drawable"])

    def get_accented_dict(self):
        """Get the accented dictionary for French, or empty dict for English."""
        if self.config["has_accents"]:
            return self.all_words.get("accented_dict", {})
        return {}

    def get_word_with_accents(self, word):
        """Get word with accents if available, otherwise return original."""
        if self.config["has_accents"]:
            accented_dict = self.get_accented_dict()
            return accented_dict.get(word, word)
        return word

    def generate_things_to_avoid(self, word, model):
        """Generate things to avoid for the given word."""
        response_model = self.config["response_model_class"]
        things_to_avoid_prompt = format_template(
            self.prompts_path / "things_to_avoid.md", word=word
        )
        client = self.get_client(model)
        return client(
            things_to_avoid_prompt,
            response_model=response_model,
            temperature=0.4,
            model=model,
            thinking_budget=None,
        )

    def play(
        self,
        word_size=5,
        word=None,
        model="gemini-2.5-flash",
        thinking_budget=None,
    ):
        """Play the interactive word guessing game."""
        words = self.all_words[str(word_size)]

        if word is None:
            word = self.get_random_word(words)
            self.debug_print(self.config["messages"]["secret_word"].format(word))
        else:
            print(self.config["messages"]["using_word"].format(word))

        print(self.config["messages"]["generating_advice"])
        word_with_accents = self.get_word_with_accents(word)
        things_to_avoid = self.generate_things_to_avoid(word_with_accents, model)
        self.debug_print(
            f"Things to avoid: {getattr(things_to_avoid, self.config['avoid_field'])}"
        )

        client = self.get_client(model)
        word_response_prompt = format_template(
            self.prompts_path / "word_response.md",
            secret_word=word_with_accents,
            avoid=", ".join(getattr(things_to_avoid, self.config["avoid_field"])),
            advice=getattr(things_to_avoid, self.config["advice_field"]),
        )

        print(self.config["messages"]["lets_play"])

        while True:
            player_word = input(self.config["messages"]["input_prompt"])
            if self.config["has_accents"]:
                player_word = player_word.upper()

            if player_word == self.config["messages"]["quit_command"]:
                print(self.config["messages"]["quit_message"].format(word))
                break

            if len(player_word) == 0:
                continue

            if len(player_word) != len(word):
                print(self.config["messages"]["length_warning"].format(len(word)))
                continue

            normalized_word = self.config["case_conversion"](player_word)
            if normalized_word not in words["playable"]:
                print(self.config["messages"]["not_in_list"].format(normalized_word))
                continue

            if normalized_word == word:
                print(self.config["messages"]["win_message"])
                break

            print(self.config["messages"]["checking"])
            player_word_with_accents = self.get_word_with_accents(normalized_word)
            response = client(
                word_response_prompt.replace(
                    "{{player_word}}", player_word_with_accents
                ),
                temperature=0.2,
                model=model,
                debug=self.debug,
                thinking_budget=thinking_budget,
            )
            print(f"\n🗣️ {response}\n")

    def run_tests(self, model="gemini-2.5-flash", word=None, thinking_budget=None):
        """Run tests on a series of words."""
        test_words = json.loads((self.prompts_path / "test_words.json").read_text())
        client = self.get_client(model)

        if word is not None:
            test_words = {word: test_words[word]}

        for word, guesses in test_words.items():
            print(f"\n{self.config['messages']['test_word_prefix'].format(word)}")
            word_with_accents = self.get_word_with_accents(word)
            things_to_avoid = self.generate_things_to_avoid(word_with_accents, model)
            word_response_prompt = format_template(
                self.prompts_path / "word_response.md",
                secret_word=word_with_accents,
                avoid=", ".join(getattr(things_to_avoid, self.config["avoid_field"])),
                advice=getattr(things_to_avoid, self.config["advice_field"]),
            )
            for guess in guesses:
                guess_with_accents = self.get_word_with_accents(guess)
                response = client(
                    word_response_prompt.replace("{{player_word}}", guess_with_accents),
                    temperature=0.2,
                    model=model,
                    debug=self.debug,
                    thinking_budget=thinking_budget,
                )
                print(response)

    def generate_batch(
        self,
        word_size=5,
        model="gemini-2.5-flash",
        word=None,
        output_file=None,
        thinking_budget=None,
        batch_function=None,
    ):
        """Generate batch responses for all playable words."""
        if batch_function is None:
            raise ValueError("batch_function is required for batch generation")

        start_time = time.time()
        words = self.all_words[str(word_size)]

        if word is None:
            word = self.get_random_word(words)

        print("Generating words to avoid")
        word_with_accents = self.get_word_with_accents(word)
        things_to_avoid = self.generate_things_to_avoid(word_with_accents, model)

        print("Generating word responses")
        word_response_prompt = format_template(
            self.prompts_path / "word_response.md",
            secret_word=word_with_accents,
            avoid=", ".join(getattr(things_to_avoid, self.config["avoid_field"])),
            advice=getattr(things_to_avoid, self.config["advice_field"]),
        )

        prompts_by_word = {
            word: word_response_prompt.replace(
                "{{player_word}}", self.get_word_with_accents(word)
            )
            for word in words["playable"]
        }

        results, _job = batch_function(
            prompts_by_word,
            model=model,
            temperature=0.2,
            gcs_bucket="verbiage-files",
            project_id="gen-lang-client-0608167298",
            location="us-central1",
            thinking_budget=thinking_budget,
        )
        results["solution"] = word

        if output_file is None:
            output_file = f"batch_{model}_{word_size}.json"

        print(f"Writing to file {output_file}")
        if output_file.endswith(".json.gz"):
            with gzip.open(output_file, "wt") as f:
                json.dump(results, f)
        else:
            with open(output_file, "w") as f:
                json.dump(results, f)
        print(f"Done in {int(time.time() - start_time)} seconds")
