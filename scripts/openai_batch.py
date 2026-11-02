"""Submit clue prompts to the OpenAI Batch API."""

import json
import re
import tempfile
import time
from pathlib import Path
from typing import Dict

from openai import OpenAI

from VerbiageGame import _openai_request_params

ENDPOINT = "/v1/chat/completions"
TERMINAL_STATES = {"completed", "failed", "expired", "cancelled"}
_SECRET_WORD = re.compile(r'\*\*Secret word:\*\* "([^"]+)"')


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
    **_unused,
) -> tuple[dict[str, str], object]:
    """Run prompts through the OpenAI Batch API and return {id: text}."""
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
    batch = _wait_for_batch(client, batch.id)
    if batch.status != "completed" or not batch.output_file_id:
        detail = _batch_error_detail(client, batch)
        raise RuntimeError(
            f"Batch {batch.id} ended with status {batch.status}: {detail}"
        )

    output = client.files.content(batch.output_file_id).text
    results = {}
    row_errors = []
    for line in output.splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        try:
            results[row["custom_id"]] = _response_text(row)
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
    return results, batch


def fetch_completed_batch(batch_id: str) -> tuple[dict[str, str], str]:
    """Download a finished batch. Returns clues and the secret word."""
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
    input_text = client.files.content(batch.input_file_id).text
    for line in input_text.splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        input_ids.append(row["custom_id"])
        content = row["body"]["messages"][0]["content"]
        match = _SECRET_WORD.search(content)
        if match is None:
            raise RuntimeError(f"{row['custom_id']} prompt has no secret word")
        secrets.add(match.group(1))
    if len(secrets) != 1:
        raise RuntimeError(f"Batch {batch.id} prompts name {len(secrets)} secret words")

    output = client.files.content(batch.output_file_id).text
    results = {}
    row_errors = []
    for line in output.splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        try:
            results[row["custom_id"]] = _response_text(row)
        except RuntimeError as exc:
            row_errors.append(str(exc))

    missing = [word for word in input_ids if word not in results]
    if missing or row_errors:
        preview = ", ".join(missing[:5])
        detail = _batch_error_detail(client, batch)
        row_preview = "\n".join(row_errors[:5])
        raise RuntimeError(
            f"Batch {batch.id} missing {len(missing)} results, including {preview}\n"
            f"{row_preview}\n{detail}"
        )

    solution = next(iter(secrets))
    print(f"Batch {batch.id} has {len(results)} clues for {solution}")
    return results, solution
