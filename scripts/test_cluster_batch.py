"""Tests for clustered clue batches and multi-clue parsing."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from VerbiageGame import (
    VerbiageGame,
    parse_cluster_members_marker,
    parse_multi_clue_response,
    parse_secret_marker,
    strip_accents,
)
from openai_batch import fetch_completed_batch


class ParseHelpersTest(unittest.TestCase):
    def test_strip_accents(self):
        self.assertEqual(strip_accents("PARÉO"), "PAREO")
        self.assertEqual(strip_accents("allée"), "allee")

    def test_parse_markers(self):
        prompt = (
            "hello\n"
            "<<verbiage_secret:APPLE>>\n"
            "<<verbiage_cluster_members:PEAR,GRAPE,MELON>>\n"
        )
        self.assertEqual(parse_secret_marker(prompt), "APPLE")
        self.assertEqual(
            parse_cluster_members_marker(prompt), ["PEAR", "GRAPE", "MELON"]
        )
        self.assertIsNone(parse_secret_marker("no marker"))
        self.assertIsNone(parse_cluster_members_marker("no marker"))

    def test_parse_multi_clue_response_valid(self):
        text = "FILM: THE WORD sits for a FILM.\nROBE: THE WORD wears a ROBE."
        clues = parse_multi_clue_response(
            text,
            ["FILM", "ROBE"],
            normalize_key=lambda word: word.upper(),
        )
        self.assertEqual(
            clues,
            {
                "FILM": "THE WORD sits for a FILM.",
                "ROBE": "THE WORD wears a ROBE.",
            },
        )

    def test_parse_multi_clue_response_rejects_bad_lines(self):
        with self.assertRaisesRegex(ValueError, "missing"):
            parse_multi_clue_response(
                "FILM: only one",
                ["FILM", "ROBE"],
                normalize_key=lambda word: word.upper(),
            )
        with self.assertRaisesRegex(ValueError, "duplicate"):
            parse_multi_clue_response(
                "FILM: a\nFILM: b\nROBE: c",
                ["FILM", "ROBE"],
                normalize_key=lambda word: word.upper(),
            )
        with self.assertRaisesRegex(ValueError, "unexpected"):
            parse_multi_clue_response(
                "FILM: a\nROBE: b\nBEAR: c",
                ["FILM", "ROBE"],
                normalize_key=lambda word: word.upper(),
            )
        with self.assertRaisesRegex(ValueError, "unparseable"):
            parse_multi_clue_response(
                "not a clue line\nFILM: a",
                ["FILM"],
                normalize_key=lambda word: word.upper(),
            )
        with self.assertRaisesRegex(ValueError, "empty clue"):
            parse_multi_clue_response(
                "FILM:",
                ["FILM"],
                normalize_key=lambda word: word.upper(),
            )


class ClusterMapTest(unittest.TestCase):
    def test_english_clusters_cover_playable_words(self):
        game = VerbiageGame(language="en")
        clusters = game.load_clusters(5)
        playable = set(game.all_words["5"]["playable"])
        found = [word for group in clusters for word in group]
        self.assertEqual(len(found), len(set(found)))
        self.assertEqual(set(found), playable)
        self.assertTrue(all(10 <= len(group) <= 11 for group in clusters))

    def test_french_clusters_cover_unique_playable_words(self):
        game = VerbiageGame(language="fr")
        clusters = game.load_clusters(5)
        playable = set(game.all_words["5"]["playable"])
        found = [word for group in clusters for word in group]
        self.assertEqual(len(found), len(set(found)))
        self.assertEqual(set(found), playable)
        self.assertTrue(all(10 <= len(group) <= 11 for group in clusters))


class PromptAndGenerationTest(unittest.TestCase):
    def test_build_multi_clue_prompt_embeds_markers_and_core(self):
        game = VerbiageGame(language="en")
        prompt = game.build_multi_clue_prompt(
            secret_word="APPLE",
            avoid="fruit, orchard",
            player_words=["PEAR", "GRAPE"],
            secret_key="APPLE",
        )
        self.assertIn('**Secret word:** "APPLE"', prompt)
        self.assertIn("- PEAR", prompt)
        self.assertIn("- GRAPE", prompt)
        self.assertIn("THE WORD", prompt)
        self.assertIn("fruit, orchard", prompt)
        self.assertIn("<<verbiage_secret:APPLE>>", prompt)
        self.assertIn("<<verbiage_cluster_members:PEAR,GRAPE>>", prompt)
        self.assertNotIn("{{core}}", prompt)
        self.assertNotIn("{{player_word}}", prompt)

    def test_format_word_response_still_single_guess(self):
        game = VerbiageGame(language="en")
        prompt = game.format_word_response(
            secret_word="APPLE",
            avoid="fruit",
        )
        self.assertIn("{{player_word}}", prompt)
        self.assertIn("THE WORD", prompt)
        self.assertNotIn("{{core}}", prompt)

    def test_french_normalize_guess_key(self):
        game = VerbiageGame(language="fr")
        self.assertEqual(game.normalize_guess_key("allée"), "ALLEE")
        self.assertEqual(game.normalize_guess_key("ALLEE"), "ALLEE")
        self.assertEqual(game.normalize_guess_key("paréo"), "PAREO")

    def test_generate_batch_by_cluster_flattens_results(self):
        game = VerbiageGame(language="en")
        selected = game.load_clusters(5)[0][:3]
        game.all_words["5"] = {"playable": selected, "drawable": ["APPLE"]}

        def fake_batch(prompts, **_kwargs):
            self.assertEqual(len(prompts), 1)
            prompt_id = next(iter(prompts))
            self.assertTrue(prompt_id.startswith("cluster-"))
            members = parse_cluster_members_marker(prompts[prompt_id])
            self.assertEqual(members, selected)
            body = "\n".join(
                f"{word}: THE WORD relates to {word}." for word in selected
            )
            return {prompt_id: body}, object()

        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "batch.json"
            with (
                patch.object(game, "generate_things_to_avoid") as avoid,
                patch.object(game, "load_clusters", return_value=[selected]),
            ):
                avoid.return_value = type(
                    "Avoid",
                    (),
                    {"avoid": ["hint"], "advice": "be careful"},
                )()
                game.generate_batch(
                    word_size=5,
                    word="APPLE",
                    output_file=output_file,
                    batch_function=fake_batch,
                    by_cluster=True,
                )
            puzzle = json.loads(output_file.read_text())
            self.assertEqual(puzzle["solution"], "APPLE")
            for word in selected:
                self.assertEqual(puzzle[word], f"THE WORD relates to {word}.")
            self.assertEqual(len(puzzle) - 1, len(selected))

    def test_generate_batch_by_cluster_rejects_malformed_response(self):
        game = VerbiageGame(language="en")
        selected = game.load_clusters(5)[0][:2]
        game.all_words["5"] = {"playable": selected, "drawable": ["APPLE"]}

        def fake_batch(prompts, **_kwargs):
            prompt_id = next(iter(prompts))
            return {prompt_id: f"{selected[0]}: only one clue"}, object()

        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "batch.json"
            with (
                patch.object(game, "generate_things_to_avoid") as avoid,
                patch.object(game, "load_clusters", return_value=[selected]),
            ):
                avoid.return_value = type(
                    "Avoid",
                    (),
                    {"avoid": ["hint"], "advice": "be careful"},
                )()
                with self.assertRaisesRegex(ValueError, "missing"):
                    game.generate_batch(
                        word_size=5,
                        word="APPLE",
                        output_file=output_file,
                        batch_function=fake_batch,
                        by_cluster=True,
                    )

    def test_run_tests_batched_one_prompt_per_secret(self):
        game = VerbiageGame(language="en")
        calls = []

        def fake_client(prompt, **kwargs):
            calls.append((prompt, kwargs.get("model")))
            return (
                "FILM: THE WORD likes FILM.\n"
                "ROBE: THE WORD wears a ROBE.\n"
                "BEAR: THE WORD faces a BEAR.\n"
                "GREY: THE WORD can look GREY."
            )

        with (
            patch.object(game, "get_client", return_value=fake_client),
            patch.object(game, "generate_things_to_avoid") as avoid,
            patch("VerbiageGame.print_usage_cost"),
        ):
            avoid.return_value = type(
                "Avoid",
                (),
                {"avoid": ["vatican"], "advice": "be careful"},
            )()
            game.run_tests_batched(model="gemini-2.5-flash", word="POPE")
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][1], "gemini-2.5-flash")
        self.assertIn("<<verbiage_secret:POPE>>", calls[0][0])
        self.assertIn("<<verbiage_cluster_members:FILM,ROBE,BEAR,GREY>>", calls[0][0])


class RecoverClusterBatchTest(unittest.TestCase):
    def test_fetch_completed_batch_parses_clusters(self):
        members = ["PEAR", "GRAPE"]
        prompt = (
            '**Secret word:** "APPLE"\n'
            "<<verbiage_secret:APPLE>>\n"
            f"<<verbiage_cluster_members:{','.join(members)}>>\n"
        )
        response_body = "\n".join(
            f"{word}: THE WORD relates to {word}." for word in members
        )
        input_row = {
            "custom_id": "cluster-0000",
            "body": {"messages": [{"content": prompt}]},
        }
        output_row = {
            "custom_id": "cluster-0000",
            "response": {
                "status_code": 200,
                "body": {"choices": [{"message": {"content": response_body}}]},
            },
        }

        class FakeFiles:
            def content(self, file_id):
                text = (
                    json.dumps(input_row)
                    if file_id == "input"
                    else json.dumps(output_row)
                )
                return type("Content", (), {"text": text})()

        class FakeBatches:
            def retrieve(self, batch_id):
                return type(
                    "Batch",
                    (),
                    {
                        "id": batch_id,
                        "status": "completed",
                        "request_counts": None,
                        "output_file_id": "output",
                        "input_file_id": "input",
                        "error_file_id": None,
                        "errors": None,
                    },
                )()

            def list(self, limit=5):
                return type("Page", (), {"data": []})()

        class FakeClient:
            def __init__(self):
                self.files = FakeFiles()
                self.batches = FakeBatches()

        with patch("openai_batch.OpenAI", return_value=FakeClient()):
            results, solution = fetch_completed_batch("batch_test", language="en")
        self.assertEqual(solution, "APPLE")
        self.assertEqual(
            results,
            {
                "PEAR": "THE WORD relates to PEAR.",
                "GRAPE": "THE WORD relates to GRAPE.",
            },
        )


if __name__ == "__main__":
    unittest.main()
