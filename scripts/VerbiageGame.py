from pathlib import Path
from typing import Optional
from pydantic import BaseModel
from google import genai
from openai import OpenAI
import json
import re
import time
import gzip
import unicodedata
from random import choice

SECRET_MARKER = re.compile(r"<<verbiage_secret:([^>]+)>>")
CLUSTER_MEMBERS_MARKER = re.compile(r"<<verbiage_cluster_members:([^>]+)>>")
CLUE_LINE = re.compile(r"^([^:\n]+):\s*(.*?)\s*$")


# USD per 1M tokens at standard rates. Output tokens include reasoning tokens.
MODEL_PRICES = {
    "gpt-6.1-terra": {
        "input": 1.0,
        "cached": 0.05,
        "cache_write": 1.25,
        "output": 5.0,
        "long_context_tokens": 272_000,
        "long_context_input_multiplier": 2.0,
        "long_context_output_multiplier": 1.5,
    }
}

OPENAI_EFFORTS = {"none", "minimal", "low", "medium", "high", "xhigh", "max"}
GEMINI_THINKING_LEVELS = {
    "minimal": "MINIMAL",
    "low": "LOW",
    "medium": "MEDIUM",
    "high": "HIGH",
}


def _usage_detail(details, name: str) -> int:
    if details is None:
        return 0
    value = getattr(details, name, None)
    if value is None:
        extra = getattr(details, "model_extra", None) or {}
        value = extra.get(name, 0)
    return value or 0


def _gemini_thinking_config(thinking_budget):
    if thinking_budget is None or thinking_budget == "":
        return None
    text = str(thinking_budget).strip().lower()
    if text in GEMINI_THINKING_LEVELS:
        return genai.types.ThinkingConfig(thinking_level=GEMINI_THINKING_LEVELS[text])
    if text == "none":
        return genai.types.ThinkingConfig(thinking_budget=0)
    return genai.types.ThinkingConfig(thinking_budget=int(text))


def _append_gemini_usage(resp, usage_log):
    if usage_log is None or resp.usage_metadata is None:
        return
    usage = resp.usage_metadata
    thoughts = getattr(usage, "thoughts_token_count", 0) or 0
    candidates = getattr(usage, "candidates_token_count", 0) or 0
    usage_log.append(
        {
            "input": getattr(usage, "prompt_token_count", 0) or 0,
            "cached": getattr(usage, "cached_content_token_count", 0) or 0,
            "cache_write": 0,
            "output": candidates + thoughts,
            "reasoning": thoughts,
        }
    )


def _append_openai_usage(completion, usage_log):
    if usage_log is None or completion.usage is None:
        return
    usage = completion.usage
    usage_log.append(
        {
            "input": usage.prompt_tokens or 0,
            "cached": _usage_detail(usage.prompt_tokens_details, "cached_tokens"),
            "cache_write": _usage_detail(
                usage.prompt_tokens_details, "cache_write_tokens"
            ),
            "output": usage.completion_tokens or 0,
            "reasoning": _usage_detail(
                usage.completion_tokens_details, "reasoning_tokens"
            ),
        }
    )


def _call_cost(model: str, record: dict) -> float | None:
    price = MODEL_PRICES.get(model)
    if price is None:
        return None
    uncached = max(record["input"] - record["cached"] - record["cache_write"], 0)
    input_multiplier = 1.0
    output_multiplier = 1.0
    if record["input"] > price["long_context_tokens"]:
        input_multiplier = price["long_context_input_multiplier"]
        output_multiplier = price["long_context_output_multiplier"]
    return (
        uncached * price["input"] * input_multiplier
        + record["cached"] * price["cached"] * input_multiplier
        + record["cache_write"] * price["cache_write"] * input_multiplier
        + record["output"] * price["output"] * output_multiplier
    ) / 1_000_000


def print_usage_cost(model: str, usage_log: list[dict]):
    """Print token totals and the estimated API cost for a finished test."""
    if not usage_log:
        return
    totals = {
        key: sum(record[key] for record in usage_log)
        for key in ("input", "cached", "cache_write", "output", "reasoning")
    }
    input_parts = [f"{totals['input']:,} input"]
    details = []
    if totals["cached"]:
        details.append(f"{totals['cached']:,} cached")
    if totals["cache_write"]:
        details.append(f"{totals['cache_write']:,} cache writes")
    if details:
        input_parts.append(f"({', '.join(details)})")
    output = f"{totals['output']:,} output"
    if totals["reasoning"]:
        output += f" (including {totals['reasoning']:,} reasoning)"
    print()
    print(f"Tokens: {' '.join(input_parts)}, {output}")

    costs = [_call_cost(model, record) for record in usage_log]
    if any(cost is None for cost in costs):
        print(f"No standard price is configured for {model}.")
        return
    amount = sum(costs)
    shown = f"${amount:.4f}" if amount >= 0.01 else f"${amount:.6f}"
    print(f"Estimated cost: {shown}")


def run_gemini(
    prompt,
    model="gpt-6.1-terra",
    response_model: Optional[BaseModel] = None,
    temperature: float = 0.0,
    debug: bool = False,
    thinking_budget=None,
    usage_log=None,
) -> BaseModel | str:
    """Get a response from the Gemini API"""
    client = genai.Client()
    params = {"temperature": temperature}
    thinking_config = _gemini_thinking_config(thinking_budget)
    if thinking_config is not None:
        params["thinking_config"] = thinking_config
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
    _append_gemini_usage(resp, usage_log)
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


def _openai_sampling_params(model: str, temperature: float | None) -> dict:
    """Return sampling params the model accepts.

    GPT-5, GPT-6, and o-series models reject any temperature other than the
    default, so those requests omit the parameter.
    """
    if temperature is None:
        return {}
    name = model.lower()
    if name.startswith(("o1", "o3", "o4", "gpt-5", "gpt-6")):
        return {}
    return {"temperature": temperature}


def _openai_request_params(model: str, temperature, thinking_budget) -> dict:
    params = _openai_sampling_params(model, temperature)
    if thinking_budget is None:
        return params
    effort = str(thinking_budget).strip().lower()
    name = model.lower()
    if effort in OPENAI_EFFORTS and name.startswith(
        ("o1", "o3", "o4", "gpt-5", "gpt-6")
    ):
        params["reasoning_effort"] = effort
    return params


def run_openai(
    prompt,
    model="gpt-6.1-terra",
    response_model: Optional[BaseModel] = None,
    temperature: float = 0.0,
    debug: bool = False,
    thinking_budget=None,
    usage_log=None,
) -> BaseModel | str:
    """Get a response from the OpenAI API"""
    client = OpenAI()

    messages = [{"role": "user", "content": prompt}]
    params = _openai_request_params(model, temperature, thinking_budget)

    if response_model is not None:
        # Use structured output with response_format
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": response_model.__name__,
                    "schema": response_model.model_json_schema(),
                },
            },
            **params,
        )
    else:
        # Standard text completion
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            **params,
        )
    _append_openai_usage(completion, usage_log)

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


def strip_accents(text: str) -> str:
    """Remove combining marks so accented French forms match playable keys."""
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(char for char in decomposed if unicodedata.category(char) != "Mn")


def parse_cluster_members_marker(prompt: str) -> list[str] | None:
    """Return the machine-readable cluster member list from a batch prompt."""
    match = CLUSTER_MEMBERS_MARKER.search(prompt)
    if match is None:
        return None
    members = [part.strip() for part in match.group(1).split(",") if part.strip()]
    return members or None


def parse_secret_marker(prompt: str) -> str | None:
    """Return the machine-readable secret word from a batch prompt."""
    match = SECRET_MARKER.search(prompt)
    return match.group(1).strip() if match else None


def parse_multi_clue_response(
    text: str,
    expected_words: list[str],
    *,
    normalize_key,
    context: str = "response",
) -> dict[str, str]:
    """Parse `WORD: SENTENCE` lines into a clue map for `expected_words`.

    Raises ValueError when lines are missing, duplicated, unexpected, empty,
    or when a clue spans more than one line.
    """
    expected = list(expected_words)
    expected_set = set(expected)
    if len(expected) != len(expected_set):
        raise ValueError(f"{context}: expected words contain duplicates")

    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    # Drop machine markers if the model echoes them.
    lines = [
        line
        for line in lines
        if not line.startswith("<<verbiage_") and not line.endswith(">>")
    ]

    clues = {}
    for line in lines:
        match = CLUE_LINE.match(line)
        if match is None:
            raise ValueError(f"{context}: unparseable line {line!r}")
        raw_word, clue = match.group(1).strip(), match.group(2).strip()
        if not clue:
            raise ValueError(f"{context}: empty clue for {raw_word!r}")
        if clue.count("\n"):
            raise ValueError(f"{context}: multi-line clue for {raw_word!r}")
        key = normalize_key(raw_word)
        if key is None:
            raise ValueError(f"{context}: unexpected word {raw_word!r}")
        if key not in expected_set:
            raise ValueError(f"{context}: unexpected word {key}")
        if key in clues:
            raise ValueError(f"{context}: duplicate word {key}")
        clues[key] = clue

    missing = [word for word in expected if word not in clues]
    if missing:
        preview = ", ".join(missing[:5])
        raise ValueError(
            f"{context}: missing {len(missing)} clues, including {preview}"
        )
    if len(clues) != len(expected):
        raise ValueError(f"{context}: expected {len(expected)} clues, got {len(clues)}")
    return {word: clues[word] for word in expected}


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
        dir = Path(__file__).parent
        self.prompts_path = dir / "instructions" / language
        self.words_path = dir / "word_lists" / language / f"{language}_words.json"

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

    def ai_play(self, clues, model, word_size, thinking_budget):
        client = self.get_client(model)
        clues = ". ".join(clues) if len(clues) > 0 else ""
        prompt = (
            f"You must guess THE WORD. "
            f"THE WORD is a {word_size}-letter non-plural common noun. "
            f"Here are clues on how THE WORD relates to other words, "
            f" but the quality of these clues is not proven: {clues}. "
            f"THE WORD is NOT one of these words!\n\n"
            f"Important: your answer should be a single {word_size}-letter word, "
            f"without formatting, for instance APPLE, DREAM, HORSE, etc."
        )
        return client(
            prompt,
            temperature=0.2,
            model=model,
            debug=self.debug,
            thinking_budget=thinking_budget,
        )

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

    def _word_response_core(self, avoid: str) -> str:
        """Shared clue rules used by single-word and multi-word prompts."""
        return format_template(self.prompts_path / "word_response_core.md", avoid=avoid)

    def format_word_response(self, secret_word: str, avoid: str, **extra) -> str:
        """Fill the single-guess clue template, including the shared core."""
        return format_template(
            self.prompts_path / "word_response.md",
            secret_word=secret_word,
            avoid=avoid,
            core=self._word_response_core(avoid),
            **extra,
        )

    def normalize_guess_key(self, raw_word: str) -> str | None:
        """Map a model-returned guess label onto a playable uppercase key."""
        cleaned = raw_word.strip().strip("*`\"'«»")
        if not cleaned:
            return None
        upper = cleaned.upper()
        if self.config["has_accents"]:
            plain = strip_accents(upper)
            accented = self.get_accented_dict()
            if plain in accented or plain in self._playable_lookup():
                return plain
            if upper in accented:
                return upper
            reverse = {value.upper(): key for key, value in accented.items()}
            reverse.update(
                {strip_accents(value.upper()): key for key, value in accented.items()}
            )
            return reverse.get(upper) or reverse.get(plain)
        return upper

    def _playable_lookup(self) -> set[str]:
        words = set()
        for size_data in self.all_words.values():
            if isinstance(size_data, dict) and "playable" in size_data:
                words.update(size_data["playable"])
        return words

    def load_clusters(self, word_size: int) -> list[list[str]]:
        """Load the committed semantic clusters for this language and size."""
        path = self.words_path.parent / "clusters.json"
        if not path.exists():
            raise FileNotFoundError(
                f"No cluster map for {self.language} at {path}. "
                "Generate and commit clusters.json first."
            )
        data = json.loads(path.read_text())
        if data.get("language") != self.language:
            raise RuntimeError(
                f"{path} is for {data.get('language')}, not {self.language}"
            )
        if data.get("word_size") != word_size:
            raise RuntimeError(
                f"{path} covers size {data.get('word_size')}, not {word_size}"
            )
        clusters = data["clusters"]
        playable = set(self.all_words[str(word_size)]["playable"])
        found = [word for group in clusters for word in group]
        if len(found) != len(set(found)):
            raise RuntimeError(f"{path} has duplicate words")
        if set(found) != playable:
            missing = sorted(playable - set(found))
            extra = sorted(set(found) - playable)
            raise RuntimeError(
                f"{path} does not match the playable list "
                f"(missing {len(missing)}, extra {len(extra)})"
            )
        return clusters

    def build_multi_clue_prompt(
        self,
        secret_word: str,
        avoid: str,
        player_words: list[str],
        *,
        secret_key: str | None = None,
    ) -> str:
        """Build one multi-guess clue prompt with recoverable metadata markers."""
        if not player_words:
            raise ValueError("player_words is empty")
        labels = [self.get_word_with_accents(word) for word in player_words]
        listed = "\n".join(f"- {label}" for label in labels)
        key = secret_key if secret_key is not None else secret_word
        return format_template(
            self.prompts_path / "word_response_batch.md",
            secret_word=secret_word,
            secret_key=key,
            avoid=avoid,
            core=self._word_response_core(avoid),
            player_words=listed,
            word_count=str(len(player_words)),
            cluster_members=",".join(player_words),
        )

    def parse_multi_clue_response(
        self, text: str, expected_words: list[str], context: str = "response"
    ) -> dict[str, str]:
        """Parse and validate a multi-guess model response for this language."""
        return parse_multi_clue_response(
            text,
            expected_words,
            normalize_key=self.normalize_guess_key,
            context=context,
        )

    def generate_things_to_avoid(
        self, word, model, thinking_budget=None, usage_log=None
    ):
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
            thinking_budget=thinking_budget,
            usage_log=usage_log,
        )

    def play(
        self,
        word_size=5,
        word=None,
        model="gpt-6.1-terra",
        thinking_budget=None,
        self_play=False,
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
        things_to_avoid = self.generate_things_to_avoid(
            word_with_accents, model, thinking_budget=thinking_budget
        )
        self.debug_print(
            f"Things to avoid: {getattr(things_to_avoid, self.config['avoid_field'])}"
        )

        client = self.get_client(model)
        avoid = ", ".join(getattr(things_to_avoid, self.config["avoid_field"]))
        word_response_prompt = self.format_word_response(
            secret_word=word_with_accents,
            avoid=avoid,
        )

        print(self.config["messages"]["lets_play"])
        clues = []

        while True:
            if self_play:
                player_word = self.ai_play(clues, model, word_size, thinking_budget)
                print(f"🤖 {player_word}")
            else:
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
            clues.append(response)
            print(f"\n🗣️ {response}\n")

    def _load_test_words(self, word=None):
        test_words = json.loads(
            (self.words_path.parent / "test_words.json").read_text()
        )
        if word is not None:
            test_words = {word: test_words[word]}
        return test_words

    def run_tests(self, model="gpt-6.1-terra", word=None, thinking_budget="low"):
        """Run tests on a series of words."""
        test_words = self._load_test_words(word)
        client = self.get_client(model)
        usage_log = []

        try:
            for word, guesses in test_words.items():
                print(f"\n{self.config['messages']['test_word_prefix'].format(word)}")
                word_with_accents = self.get_word_with_accents(word)
                things_to_avoid = self.generate_things_to_avoid(
                    word_with_accents,
                    model,
                    thinking_budget=thinking_budget,
                    usage_log=usage_log,
                )
                avoid = ", ".join(getattr(things_to_avoid, self.config["avoid_field"]))
                word_response_prompt = self.format_word_response(
                    secret_word=word_with_accents,
                    avoid=avoid,
                )
                for guess in guesses:
                    guess_with_accents = self.get_word_with_accents(guess)
                    response = client(
                        word_response_prompt.replace(
                            "{{player_word}}", guess_with_accents
                        ),
                        temperature=0.2,
                        model=model,
                        debug=self.debug,
                        thinking_budget=thinking_budget,
                        usage_log=usage_log,
                    )
                    print(response)
        finally:
            print_usage_cost(model, usage_log)

    def run_tests_batched(
        self, model="gpt-6.1-terra", word=None, thinking_budget="low"
    ):
        """Run tests with one multi-clue prompt per secret, via the normal API."""
        test_words = self._load_test_words(word)
        client = self.get_client(model)
        usage_log = []

        try:
            for word, guesses in test_words.items():
                print(f"\n{self.config['messages']['test_word_prefix'].format(word)}")
                word_with_accents = self.get_word_with_accents(word)
                things_to_avoid = self.generate_things_to_avoid(
                    word_with_accents,
                    model,
                    thinking_budget=thinking_budget,
                    usage_log=usage_log,
                )
                avoid = ", ".join(getattr(things_to_avoid, self.config["avoid_field"]))
                prompt = self.build_multi_clue_prompt(
                    secret_word=word_with_accents,
                    avoid=avoid,
                    player_words=list(guesses),
                    secret_key=word,
                )
                response = client(
                    prompt,
                    temperature=0.2,
                    model=model,
                    debug=self.debug,
                    thinking_budget=thinking_budget,
                    usage_log=usage_log,
                )
                clues = self.parse_multi_clue_response(
                    response, list(guesses), context=f"test {word}"
                )
                for guess in guesses:
                    print(f"{guess}: {clues[guess]}")
        finally:
            print_usage_cost(model, usage_log)

    def _cluster_prompt_groups(
        self, words_for_clues: list[str], word_size: int
    ) -> list[tuple[str, list[str]]]:
        """Build (prompt_id, members) groups for the selected playable words."""
        selected = list(dict.fromkeys(words_for_clues))
        selected_set = set(selected)
        groups = []
        covered = set()
        for index, cluster in enumerate(self.load_clusters(word_size)):
            members = [word for word in cluster if word in selected_set]
            if not members:
                continue
            groups.append((f"cluster-{index:04d}", members))
            covered.update(members)
        missing = [word for word in selected if word not in covered]
        if missing:
            preview = ", ".join(missing[:5])
            raise RuntimeError(
                f"cluster map missed {len(missing)} selected words, including {preview}"
            )
        return groups

    def generate_batch(
        self,
        word_size=5,
        model="gpt-6.1-terra",
        word=None,
        output_file=None,
        thinking_budget=None,
        batch_function=None,
        max_words=None,
        words_to_exclude=None,
        by_cluster=False,
    ):
        """Generate batch responses for all playable words."""
        if batch_function is None:
            raise ValueError("batch_function is required for batch generation")

        start_time = time.time()
        words = self.all_words[str(word_size)]

        if word is None:
            list_of_words = words["drawable"]
            if words_to_exclude is not None:
                list_of_words = [w for w in list_of_words if w not in words_to_exclude]
            word = choice(list_of_words)

        print("Generating words to avoid")
        word_with_accents = self.get_word_with_accents(word)
        things_to_avoid = self.generate_things_to_avoid(
            word_with_accents, model, thinking_budget=thinking_budget
        )
        avoid = ", ".join(getattr(things_to_avoid, self.config["avoid_field"]))

        words_for_clues = list(dict.fromkeys(words["playable"]))
        if max_words is not None:
            words_for_clues = words_for_clues[:max_words]

        if by_cluster:
            print("Generating clustered word responses")
            groups = self._cluster_prompt_groups(words_for_clues, word_size)
            prompts = {
                prompt_id: self.build_multi_clue_prompt(
                    secret_word=word_with_accents,
                    avoid=avoid,
                    player_words=members,
                    secret_key=word,
                )
                for prompt_id, members in groups
            }
            members_by_id = dict(groups)
            print(f"Submitting {len(prompts)} cluster prompts")
        else:
            print("Generating word responses")
            word_response_prompt = self.format_word_response(
                secret_word=word_with_accents,
                avoid=avoid,
            )
            prompts = {
                guess: word_response_prompt.replace(
                    "{{player_word}}", self.get_word_with_accents(guess)
                )
                for guess in words_for_clues
            }
            members_by_id = None

        raw_results, _job = batch_function(
            prompts,
            model=model,
            temperature=0.2,
            gcs_bucket="verbiage-files",
            project_id="gen-lang-client-0608167298",
            location="us-central1",
            thinking_budget=thinking_budget,
        )

        if by_cluster:
            results = {}
            for prompt_id, members in members_by_id.items():
                response = raw_results.get(prompt_id, "")
                parsed = self.parse_multi_clue_response(
                    response, members, context=prompt_id
                )
                overlap = set(parsed) & set(results)
                if overlap:
                    raise RuntimeError(
                        f"{prompt_id} repeated already-parsed words: "
                        f"{', '.join(sorted(overlap)[:5])}"
                    )
                results.update(parsed)
            missing = [guess for guess in words_for_clues if guess not in results]
            if missing:
                preview = ", ".join(missing[:5])
                raise RuntimeError(
                    f"cluster batch missing {len(missing)} clues, including {preview}"
                )
        else:
            results = raw_results

        results["solution"] = word

        if output_file is None:
            output_file = f"batch_{model}_{word_size}.json"
        output_file = Path(output_file)

        print(f"Writing to file {output_file}")
        if output_file.name.endswith(".json.gz"):
            with gzip.open(output_file, "wt") as f:
                json.dump(results, f)
        else:
            with open(output_file, "w") as f:
                json.dump(results, f)
        print(f"Done in {int(time.time() - start_time)} seconds")
