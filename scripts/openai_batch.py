"""Submit clue prompts to the OpenAI Batch API."""

import json
import re
import tempfile
import time
from pathlib import Path
from typing import Dict

from openai import OpenAI

from VerbiageGame import (
    BATCH_PRICE_RATE,
    VerbiageGame,
    _openai_request_params,
    parse_avoid_list,
    parse_cluster_members_marker,
    parse_guidance,
    parse_secret_marker,
    usage_record_from_openai_usage,
)

ENDPOINT = "/v1/chat/completions"
TERMINAL_STATES = {"completed", "failed", "expired", "cancelled"}
_SECRET_WORD = re.compile(r'\*\*Secret word:\*\* "([^"]+)"')
_SECRET_WORD_FR = re.compile(r"\*\*Mot secret :\*\* «\s*([^»]+?)\s*»")


def _request_line(custom_id: str, prompt: str, model: str, body_params: dict) -> str:
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        **body_params,
    }
    return json.dumps(
        {
            "custom_id": custom_id,
            "method": "POST",
            "url": ENDPOINT,
            "body": body,
        }
    )


def _wait_for_batch(client: OpenAI, batch_id: str):
    while True:
        batch = client.batches.retrieve(batch_id)
        counts = batch.request_counts
        progress = ""
        if counts is not None:
            progress = (
                f" ({counts.completed}/{counts.total} completed,"
                f" {counts.failed} failed)"
            )
        print(f"Batch {batch.id} status: {batch.status}{progress}")
        if batch.status in TERMINAL_STATES:
            return batch
        time.sleep(10)


def _batch_error_detail(client: OpenAI, batch) -> str:
    """Summarize a batch's error object and the first rows of its error file."""
    parts = []
    if getattr(batch, "errors", None):
        parts.append(str(batch.errors)[:2000])
    error_file_id = getattr(batch, "error_file_id", None)
    if error_file_id:
        try:
            text = client.files.content(error_file_id).text
        except Exception as exc:
            parts.append(f"Could not read error file {error_file_id}: {exc}")
        else:
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            preview = "\n".join(line[:500] for line in lines[:5])
            parts.append(f"Error file has {len(lines)} row(s):\n{preview}")
    return "\n".join(parts) if parts else "no error details"


def batch_usage_record(row: dict) -> dict | None:
    """Read token usage from a batch output row, priced at the batch rate."""
    body = (row.get("response") or {}).get("body") or {}
    usage = body.get("usage")
    if not isinstance(usage, dict):
        return None
    record = usage_record_from_openai_usage(usage)
    record["rate"] = BATCH_PRICE_RATE
    return record


def _response_text(row: dict) -> str:
    custom_id = row.get("custom_id", "?")
    if row.get("error"):
        raise RuntimeError(f"{custom_id} failed: {row['error']}")
    response = row.get("response") or {}
    if response.get("status_code") != 200:
        detail = response.get("body") or response
        raise RuntimeError(f"{custom_id} failed: {detail}")
    return response["body"]["choices"][0]["message"]["content"]


def openai_batch(
    prompts: Dict[str, str],
    model: str = "gpt-6.1-terra",
    temperature: float = 0.2,
    thinking_budget: str = "low",
    wait: bool = True,
    **_unused,
) -> tuple[dict[str, str], object] | tuple[dict[str, str], object, list[dict]]:
    """Run prompts through the OpenAI Batch API.

    When wait is false, return as soon as the batch id exists. The result
    map is empty and there is no usage log yet.
    """
    if not prompts:
        raise ValueError("prompts is empty")

    client = OpenAI()
    body_params = _openai_request_params(model, temperature, thinking_budget)
    lines = [
        _request_line(custom_id, prompt, model, body_params)
        for custom_id, prompt in prompts.items()
    ]

    with tempfile.NamedTemporaryFile(
        "w", suffix=".jsonl", delete=False, encoding="utf-8"
    ) as handle:
        handle.write("\n".join(lines))
        handle.write("\n")
        path = Path(handle.name)

    try:
        with path.open("rb") as handle:
            uploaded = client.files.create(file=handle, purpose="batch")
    finally:
        path.unlink()

    batch = client.batches.create(
        input_file_id=uploaded.id,
        endpoint=ENDPOINT,
        completion_window="24h",
    )
    print(f"Batch created: {batch.id}")
    if not wait:
        return {}, batch
    batch = _wait_for_batch(client, batch.id)
    if batch.status != "completed" or not batch.output_file_id:
        detail = _batch_error_detail(client, batch)
        raise RuntimeError(
            f"Batch {batch.id} ended with status {batch.status}: {detail}"
        )

    output = client.files.content(batch.output_file_id).text
    results = {}
    usage_records = []
    missing_usage = 0
    row_errors = []
    for line in output.splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        try:
            results[row["custom_id"]] = _response_text(row)
            record = batch_usage_record(row)
            if record is None:
                missing_usage += 1
            else:
                usage_records.append(record)
        except RuntimeError as exc:
            row_errors.append(str(exc))

    missing = [word for word in prompts if word not in results]
    if missing or row_errors:
        preview = ", ".join(missing[:5])
        detail = _batch_error_detail(client, batch)
        row_preview = "\n".join(row_errors[:5])
        raise RuntimeError(
            f"Batch {batch.id} missing {len(missing)} results, including {preview}\n"
            f"{row_preview}\n{detail}"
        )

    print(f"Successfully processed {len(results)} results")
    if missing_usage:
        print(
            f"{missing_usage} batch results included no token usage, "
            "so the estimated cost is incomplete."
        )
    return results, batch, usage_records


def _prompt_secret(content: str, custom_id: str) -> str:
    """Read the secret word from a prompt, preferring the machine marker."""
    marked = parse_secret_marker(content)
    if marked:
        return marked
    match = _SECRET_WORD.search(content) or _SECRET_WORD_FR.search(content)
    if match is None:
        raise RuntimeError(f"{custom_id} prompt has no secret word")
    return match.group(1).strip()


def fetch_completed_batch(
    batch_id: str, language: str = "en"
) -> tuple[dict[str, str], str]:
    """Download a finished batch. Returns clues and the secret word.

    Cluster batches are detected from the machine-readable members marker in
    each input prompt. Those responses are parsed into the flat puzzle schema.
    """
    client = OpenAI()
    batch = client.batches.retrieve(batch_id)
    print(
        f"Batch {batch.id} status={batch.status} "
        f"counts={batch.request_counts} output={batch.output_file_id}"
    )
    if batch.status not in TERMINAL_STATES:
        batch = _wait_for_batch(client, batch.id)
    if batch.status != "completed" or not batch.output_file_id:
        recent = client.batches.list(limit=5)
        for item in recent.data:
            print(
                f"recent {item.id} status={item.status} "
                f"counts={item.request_counts} created={item.created_at}"
            )
        detail = _batch_error_detail(client, batch)
        raise RuntimeError(
            f"Batch {batch.id} ended with status {batch.status}: {detail}"
        )

    input_ids = []
    secrets = set()
    members_by_id = {}
    input_text = client.files.content(batch.input_file_id).text
    for line in input_text.splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        custom_id = row["custom_id"]
        input_ids.append(custom_id)
        content = row["body"]["messages"][0]["content"]
        secrets.add(_prompt_secret(content, custom_id))
        members = parse_cluster_members_marker(content)
        if members is not None:
            members_by_id[custom_id] = members
    if len(secrets) != 1:
        raise RuntimeError(f"Batch {batch.id} prompts name {len(secrets)} secret words")
    if members_by_id and len(members_by_id) != len(input_ids):
        raise RuntimeError(
            f"Batch {batch.id} mixes clustered and per-word prompts "
            f"({len(members_by_id)} clustered of {len(input_ids)})"
        )

    output = client.files.content(batch.output_file_id).text
    raw_results = {}
    row_errors = []
    for line in output.splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        try:
            raw_results[row["custom_id"]] = _response_text(row)
        except RuntimeError as exc:
            row_errors.append(str(exc))

    missing = [word for word in input_ids if word not in raw_results]
    if missing or row_errors:
        preview = ", ".join(missing[:5])
        detail = _batch_error_detail(client, batch)
        row_preview = "\n".join(row_errors[:5])
        raise RuntimeError(
            f"Batch {batch.id} missing {len(missing)} results, including {preview}\n"
            f"{row_preview}\n{detail}"
        )

    solution = next(iter(secrets))
    if not members_by_id:
        print(f"Batch {batch.id} has {len(raw_results)} clues for {solution}")
        return raw_results, solution

    game = VerbiageGame(language=language)
    results = {}
    for custom_id, members in members_by_id.items():
        parsed = game.parse_multi_clue_response(
            raw_results[custom_id], members, context=custom_id
        )
        overlap = set(parsed) & set(results)
        if overlap:
            raise RuntimeError(
                f"{custom_id} repeated already-parsed words: "
                f"{', '.join(sorted(overlap)[:5])}"
            )
        results.update(parsed)
    print(
        f"Batch {batch.id} recovered {len(results)} clues "
        f"from {len(members_by_id)} clusters for {solution}"
    )
    return results, solution


def process_completed_batch(
    batch_id: str,
    language: str = "en",
    model: str = "gpt-6.1-terra",
    thinking_budget: str = "low",
    debug: bool = False,
    review_quality: bool = False,
) -> tuple[dict[str, str], str, list[dict]]:
    """Download a finished batch, fill missing clues live, and return usage.

    The returned usage log prices batch rows at the batch rate and any
    follow-up calls at the standard rate. The caller prints that cost.
    """
    client = OpenAI()
    batch = client.batches.retrieve(batch_id)
    print(
        f"Batch {batch.id} status={batch.status} "
        f"counts={batch.request_counts} output={batch.output_file_id}"
    )
    if batch.status not in TERMINAL_STATES:
        batch = _wait_for_batch(client, batch.id)
    if batch.status != "completed" or not batch.output_file_id:
        detail = _batch_error_detail(client, batch)
        raise RuntimeError(
            f"Batch {batch.id} ended with status {batch.status}: {detail}"
        )

    input_ids = []
    prompts = {}
    secrets = set()
    secret_word = None
    members_by_id = {}
    input_text = client.files.content(batch.input_file_id).text
    for line in input_text.splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        custom_id = row["custom_id"]
        content = row["body"]["messages"][0]["content"]
        input_ids.append(custom_id)
        prompts[custom_id] = content
        secrets.add(_prompt_secret(content, custom_id))
        if secret_word is None:
            display = _SECRET_WORD.search(content) or _SECRET_WORD_FR.search(content)
            secret_word = display.group(1).strip() if display else None
        members = parse_cluster_members_marker(content)
        if members is not None:
            members_by_id[custom_id] = members
    if len(secrets) != 1:
        raise RuntimeError(f"Batch {batch.id} prompts name {len(secrets)} secret words")
    if members_by_id and len(members_by_id) != len(input_ids):
        raise RuntimeError(
            f"Batch {batch.id} mixes clustered and per-word prompts "
            f"({len(members_by_id)} clustered of {len(input_ids)})"
        )
    solution = next(iter(secrets))
    if secret_word is None:
        secret_word = solution

    output = client.files.content(batch.output_file_id).text
    raw_results = {}
    usage_log = []
    missing_usage = 0
    for line in output.splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        try:
            raw_results[row["custom_id"]] = _response_text(row)
        except RuntimeError as exc:
            print(exc)
            continue
        record = batch_usage_record(row)
        if record is None:
            missing_usage += 1
            continue
        usage_log.append(record)
    if missing_usage:
        print(
            f"{missing_usage} batch results included no token usage, "
            "so the estimated cost is incomplete."
        )

    game = VerbiageGame(language=language, debug=debug)
    sense, advice = (
        parse_guidance(next(iter(prompts.values()))) if prompts else (None, None)
    )
    if not members_by_id:
        results = game.complete_clue_results(
            raw_results,
            input_ids,
            secret_word=secret_word,
            avoid=_avoid_from_prompts(prompts),
            secret_key=solution,
            model=model,
            thinking_budget=thinking_budget,
            usage_log=usage_log,
            sense=sense,
            advice=advice,
            review_quality=review_quality,
        )
        print(f"Batch {batch.id} has {len(results)} clues for {solution}")
        return results, solution, usage_log

    avoid = _avoid_from_prompts(prompts)
    results = game.complete_cluster_results(
        raw_results,
        members_by_id,
        secret_word=secret_word,
        avoid=avoid,
        secret_key=solution,
        model=model,
        thinking_budget=thinking_budget,
        usage_log=usage_log,
        sense=sense,
        advice=advice,
        review_quality=review_quality,
    )
    print(
        f"Batch {batch.id} has {len(results)} clues "
        f"from {len(members_by_id)} clusters for {solution}"
    )
    return results, solution, usage_log


def _avoid_from_prompts(prompts: dict[str, str]) -> str | None:
    """Read the shared avoid list from the prompts that were submitted."""
    for content in prompts.values():
        avoid = parse_avoid_list(content)
        if avoid:
            return avoid
    return None
