"""Tests for clustered clue batches and multi-clue parsing."""

import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from VerbiageGame import (
    VerbiageGame,
    collect_multi_clue_response,
    parse_avoid_list,
    parse_cluster_members_marker,
    parse_multi_clue_response,
    parse_secret_marker,
    print_usage_cost,
    strip_accents,
)
from openai_batch import (
    batch_usage_record,
    fetch_completed_batch,
    openai_batch,
    process_completed_batch,
)


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

    def test_generate_batch_by_cluster_follows_up_missing_words(self):
        game = VerbiageGame(language="en")
        selected = game.load_clusters(5)[0][:2]
        game.all_words["5"] = {"playable": selected, "drawable": ["APPLE"]}
        calls = []

        def fake_batch(prompts, **_kwargs):
            prompt_id = next(iter(prompts))
            return {prompt_id: f"{selected[0]}: only one clue"}, object()

        def fake_client(prompt, **_kwargs):
            calls.append(prompt)
            return f"{selected[1]}: THE WORD relates to {selected[1]}."

        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "batch.json"
            with (
                patch.object(game, "generate_things_to_avoid") as avoid,
                patch.object(game, "load_clusters", return_value=[selected]),
                patch.object(game, "get_client", return_value=fake_client),
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
        self.assertEqual(len(calls), 1)
        self.assertIn(f"<<verbiage_cluster_members:{selected[1]}>>", calls[0])
        self.assertNotIn(selected[0], calls[0])
        self.assertEqual(puzzle[selected[0]], "only one clue")
        self.assertEqual(puzzle[selected[1]], f"THE WORD relates to {selected[1]}.")
        self.assertEqual(puzzle["solution"], "APPLE")

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


class UsageCostTest(unittest.TestCase):
    def test_batch_usage_record_reads_token_details(self):
        row = {
            "custom_id": "cluster-0000",
            "response": {
                "status_code": 200,
                "body": {
                    "choices": [{"message": {"content": "FILM: hi"}}],
                    "usage": {
                        "prompt_tokens": 10,
                        "completion_tokens": 4,
                        "prompt_tokens_details": {
                            "cached_tokens": 2,
                            "cache_write_tokens": 1,
                        },
                        "completion_tokens_details": {"reasoning_tokens": 3},
                    },
                },
            },
        }
        record = batch_usage_record(row)
        self.assertEqual(
            record,
            {
                "input": 10,
                "cached": 2,
                "cache_write": 1,
                "output": 4,
                "reasoning": 3,
                "rate": 0.5,
            },
        )
        self.assertIsNone(
            batch_usage_record(
                {"response": {"status_code": 200, "body": {"choices": []}}}
            )
        )

    def test_print_usage_cost_prices_batch_rows_at_half_rate(self):
        standard = {
            "input": 10_000,
            "cached": 0,
            "cache_write": 0,
            "output": 0,
            "reasoning": 0,
        }
        batch = {**standard, "rate": 0.5}
        buffer = StringIO()
        with redirect_stdout(buffer):
            print_usage_cost("gpt-6.1-terra", [standard, batch])
        text = buffer.getvalue()
        self.assertIn("20,000 input", text)
        self.assertIn("Estimated cost: $0.0150", text)
        self.assertIn("half the standard rate", text)

        buffer = StringIO()
        with redirect_stdout(buffer):
            print_usage_cost("gpt-6.1-terra", [standard])
        text = buffer.getvalue()
        self.assertIn("Estimated cost: $0.0100", text)
        self.assertNotIn("half the standard rate", text)

    def test_generate_batch_prices_avoid_call_and_batch_rows(self):
        game = VerbiageGame(language="en")
        selected = ["FILM", "ROBE"]
        game.all_words["5"] = {"playable": selected, "drawable": ["APPLE"]}
        avoid_record = {
            "input": 100,
            "cached": 0,
            "cache_write": 0,
            "output": 20,
            "reasoning": 0,
        }
        batch_record = {
            "input": 1000,
            "cached": 0,
            "cache_write": 0,
            "output": 50,
            "reasoning": 0,
            "rate": 0.5,
        }

        def fake_avoid(*_args, usage_log=None, **_kwargs):
            usage_log.append(avoid_record)
            return type("Avoid", (), {"avoid": ["hint"], "advice": "be careful"})()

        def fake_batch(prompts, **_kwargs):
            prompt_id = next(iter(prompts))
            body = "\n".join(
                f"{word}: THE WORD relates to {word}." for word in selected
            )
            return {prompt_id: body}, object(), [batch_record]

        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "batch.json"
            with (
                patch.object(game, "generate_things_to_avoid", side_effect=fake_avoid),
                patch.object(game, "load_clusters", return_value=[selected]),
                patch("VerbiageGame.print_usage_cost") as cost,
            ):
                game.generate_batch(
                    word_size=5,
                    word="APPLE",
                    output_file=output_file,
                    batch_function=fake_batch,
                    by_cluster=True,
                )
        cost.assert_called_once_with("gpt-6.1-terra", [avoid_record, batch_record])


class ProcessBatchTest(unittest.TestCase):
    def test_collect_reports_omitted_word(self):
        text = "\n".join(
            f"{word}: THE WORD relates to {word}."
            for word in ("FRYER", "GRILL", "STOVE")
        )
        found, missing = collect_multi_clue_response(
            text,
            ["FRYER", "GRILL", "ROAST", "STOVE"],
            normalize_key=lambda word: word.upper(),
        )
        self.assertEqual(list(found), ["FRYER", "GRILL", "STOVE"])
        self.assertEqual(missing, ["ROAST"])

    def test_parse_avoid_list_from_real_prompt(self):
        game = VerbiageGame(language="en")
        prompt = game.build_multi_clue_prompt(
            secret_word="APPLE",
            avoid="hint, clue",
            player_words=["PEAR", "GRAPE"],
            secret_key="APPLE",
        )
        self.assertEqual(parse_avoid_list(prompt), "hint, clue")
        french = VerbiageGame(language="fr").build_multi_clue_prompt(
            secret_word="POMME",
            avoid="chose, truc",
            player_words=["POIRE"],
            secret_key="POMME",
        )
        self.assertEqual(parse_avoid_list(french), "chose, truc")

    def test_process_completed_batch_follows_up_and_prices(self):
        game = VerbiageGame(language="en")
        prompt = game.build_multi_clue_prompt(
            secret_word="APPLE",
            avoid="hint, clue",
            player_words=["PEAR", "GRAPE"],
            secret_key="APPLE",
        )
        input_row = {
            "custom_id": "cluster-0000",
            "body": {"model": "gpt-6.1-terra", "messages": [{"content": prompt}]},
        }
        output_row = {
            "custom_id": "cluster-0000",
            "response": {
                "status_code": 200,
                "body": {
                    "model": "gpt-6.1-terra",
                    "choices": [
                        {"message": {"content": "PEAR: THE WORD relates to PEAR."}}
                    ],
                    "usage": {"prompt_tokens": 10_000, "completion_tokens": 0},
                },
            },
        }
        follow_record = {
            "input": 10_000,
            "cached": 0,
            "cache_write": 0,
            "output": 0,
            "reasoning": 0,
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

        class FakeClient:
            def __init__(self):
                self.files = FakeFiles()
                self.batches = FakeBatches()

        def fake_chat(prompt_text, **kwargs):
            self.assertIn("<<verbiage_cluster_members:GRAPE>>", prompt_text)
            self.assertIn("hint, clue", prompt_text)
            kwargs["usage_log"].append(follow_record)
            return "GRAPE: THE WORD relates to GRAPE."

        with (
            patch("openai_batch.OpenAI", return_value=FakeClient()),
            patch("openai_batch.VerbiageGame.get_client", return_value=fake_chat),
        ):
            results, solution, usage_log = process_completed_batch(
                "batch_test", language="en", model="gpt-6.1-terra"
            )
        self.assertEqual(solution, "APPLE")
        self.assertEqual(
            results,
            {
                "PEAR": "THE WORD relates to PEAR.",
                "GRAPE": "THE WORD relates to GRAPE.",
            },
        )
        self.assertEqual(usage_log[0]["rate"], 0.5)
        self.assertEqual(usage_log[1], follow_record)
        buffer = StringIO()
        with redirect_stdout(buffer):
            print_usage_cost("gpt-6.1-terra", usage_log)
        text = buffer.getvalue()
        self.assertIn("Estimated cost: $0.0150", text)
        self.assertIn("half the standard rate", text)

    def test_process_batch_command_prints_cost(self):
        from click.testing import CliRunner

        from game import main

        usage_log = [
            {
                "input": 20_000,
                "cached": 0,
                "cache_write": 0,
                "output": 0,
                "reasoning": 0,
                "rate": 0.5,
                "model": "gpt-6.1-terra",
            }
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "puzzle.json"
            with patch(
                "game.process_completed_batch",
                return_value=({"PEAR": "a clue"}, "APPLE", usage_log),
            ):
                result = CliRunner().invoke(
                    main,
                    [
                        "process-finished-batch",
                        "batch_test",
                        "--lang",
                        "en",
                        "--output-file",
                        str(output_file),
                    ],
                )
            puzzle = json.loads(output_file.read_text())
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(puzzle["solution"], "APPLE")
        self.assertIn("Estimated cost: $0.0100", result.output)
        self.assertIn("half the standard rate", result.output)

    def test_openai_batch_returns_id_without_waiting(self):
        class FakeFiles:
            def create(self, file, purpose):
                return type("Upload", (), {"id": "file_1"})()

        class FakeBatches:
            def create(self, **_kwargs):
                return type("Batch", (), {"id": "batch_new"})()

            def retrieve(self, _batch_id):
                raise AssertionError("launch should not wait for the batch")

        class FakeClient:
            def __init__(self):
                self.files = FakeFiles()
                self.batches = FakeBatches()

        with patch("openai_batch.OpenAI", return_value=FakeClient()):
            results, batch = openai_batch({"APPLE": "Say hello."}, wait=False)
        self.assertEqual(results, {})
        self.assertEqual(batch.id, "batch_new")

    def test_launch_daily_batch_writes_queue_once(self):
        from click.testing import CliRunner

        from game import main

        calls = []

        def fake_batch(prompts, **kwargs):
            calls.append(kwargs["wait"])
            self.assertIn("<<verbiage_secret:APPLE>>", next(iter(prompts.values())))
            return {}, type("Batch", (), {"id": "batch_queued"})()

        def fake_avoid(self, word, model, thinking_budget=None, usage_log=None):
            return type("Avoid", (), {"avoid": ["hint"], "advice": "careful"})()

        with tempfile.TemporaryDirectory() as temp_dir:
            queue = Path(temp_dir) / "2099-01-01.json"
            with (
                patch("game.openai_batch", side_effect=fake_batch),
                patch("game.batch_queue_path", return_value=queue),
                patch(
                    "VerbiageGame.VerbiageGame.generate_things_to_avoid",
                    fake_avoid,
                ),
            ):
                runner = CliRunner()
                args = [
                    "launch-daily-batch",
                    "--language",
                    "en",
                    "--date",
                    "2099-01-01",
                    "--word",
                    "APPLE",
                ]
                first = runner.invoke(main, args)
                second = runner.invoke(main, args)
            queued = json.loads(queue.read_text())
        self.assertEqual(first.exit_code, 0, first.output)
        self.assertEqual(second.exit_code, 0, second.output)
        self.assertEqual(calls, [False])
        self.assertEqual(queued, {"word": "APPLE", "batch_id": "batch_queued"})
        self.assertIn("Queued APPLE for 2099-01-01 as batch_queued", first.output)
        self.assertIn("already queued", second.output)

    def test_process_finished_batch_reads_queue(self):
        from click.testing import CliRunner

        from game import main

        usage_log = [
            {
                "input": 20_000,
                "cached": 0,
                "cache_write": 0,
                "output": 0,
                "reasoning": 0,
                "rate": 0.5,
            }
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            queue = Path(temp_dir) / "2099-01-01.json"
            queue.write_text(
                json.dumps({"word": "APPLE", "batch_id": "batch_from_queue"}) + "\n"
            )
            output_file = Path(temp_dir) / "puzzle.json"
            with (
                patch("game.batch_queue_path", return_value=queue),
                patch("game._record_calendar_date"),
                patch(
                    "game.process_completed_batch",
                    return_value=({"PEAR": "a clue"}, "APPLE", usage_log),
                ) as process,
            ):
                result = CliRunner().invoke(
                    main,
                    [
                        "process-finished-batch",
                        "--lang",
                        "en",
                        "--date",
                        "2099-01-01",
                        "--output-file",
                        str(output_file),
                    ],
                )
            puzzle = json.loads(output_file.read_text())
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(process.call_args.args[0], "batch_from_queue")
        self.assertEqual(puzzle["solution"], "APPLE")
        self.assertIn("Queued word for 2099-01-01: APPLE", result.output)

        missing = CliRunner().invoke(
            main,
            ["process-finished-batch", "--language", "en", "--date", "2099-01-02"],
        )
        self.assertEqual(missing.exit_code, 0, missing.output)
        self.assertIn("No batch queued", missing.output)


if __name__ == "__main__":
    unittest.main()
