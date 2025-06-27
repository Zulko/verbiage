import time
import json
import tempfile
import os
from pathlib import Path
from typing import Dict, Optional
from google import genai
from google.genai.types import CreateBatchJobConfig, JobState, HttpOptions
from google.cloud import storage


def _create_batch_request(
    prompt_id: str, prompt_text: str, temperature: float, thinking_budget: 0
) -> str:
    """Create a single batch request object for the Gemini API

    Args:
        prompt_id: Unique identifier for this prompt
        prompt_text: The actual prompt text
        temperature: Temperature setting for generation

    Returns:
        JSON string containing the formatted request for the batch API
    """
    return json.dumps(
        {
            "custom_id": prompt_id,
            "request": {
                "contents": [{"role": "user", "parts": [{"text": prompt_text}]}],
                "generationConfig": {
                    "temperature": temperature,
                    "responseMimeType": "text/plain",
                    "thinkingType": "PARTIAL" if thinking else "NONE",
                },
                "thinkingConfig": {"thinkingBudget": thinking_budget},
            },
        }
    )


def _parse_result_line(line: str) -> tuple[str | None, str]:
    """Parse a single result line from batch output

    Args:
        line: JSON line string from batch output

    Returns:
        Tuple of (prompt_id, response_text). prompt_id is None if parsing fails.
    """
    try:
        result = json.loads(line)
        custom_id = result.get("custom_id")

        # Extract the response text from the result
        response_text = ""
        if "response" in result:
            candidates = result["response"].get("candidates", [])
            if candidates and len(candidates) > 0:
                content = candidates[0].get("content", {})
                parts = content.get("parts", [])
                if parts and len(parts) > 0:
                    response_text = parts[0].get("text", "")

        return custom_id, response_text
    except json.JSONDecodeError:
        return None, ""


def _upload_to_gcs(
    local_file_path: str,
    bucket_name: str,
    blob_name: Optional[str] = None,
    project_id: Optional[str] = None,
) -> str:
    """Upload a file to Google Cloud Storage

    Args:
        local_file_path: Path to the local file to upload
        bucket_name: Name of the GCS bucket
        blob_name: Name for the blob in GCS. If None, uses the filename
        project_id: GCP project ID. If None, uses default from environment

    Returns:
        GCS URI of the uploaded file (gs://bucket/blob)
    """
    if blob_name is None:
        blob_name = Path(local_file_path).name

    # Initialize the GCS client
    if project_id:
        client = storage.Client(project=project_id)
    else:
        client = storage.Client()

    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)

    # Upload the file
    blob.upload_from_filename(local_file_path)

    return f"gs://{bucket_name}/{blob_name}"


def _download_from_gcs(
    gcs_uri: str,
    local_file_path: str,
    project_id: Optional[str] = None,
) -> None:
    """Download a file from Google Cloud Storage

    Args:
        gcs_uri: GCS URI of the file to download (gs://bucket/blob)
        local_file_path: Local path where to save the downloaded file
        project_id: GCP project ID. If None, uses default from environment
    """
    # Parse the GCS URI
    if not gcs_uri.startswith("gs://"):
        raise ValueError(f"Invalid GCS URI: {gcs_uri}")

    uri_parts = gcs_uri[5:].split("/", 1)  # Remove 'gs://' and split
    if len(uri_parts) != 2:
        raise ValueError(f"Invalid GCS URI format: {gcs_uri}")

    bucket_name, blob_name = uri_parts

    # Initialize the GCS client
    if project_id:
        client = storage.Client(project=project_id)
    else:
        client = storage.Client()

    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)

    # Download the file
    blob.download_to_filename(local_file_path)


def _list_gcs_blobs(
    bucket_name: str,
    prefix: str,
    project_id: Optional[str] = None,
) -> list[str]:
    """List blobs in a GCS bucket with a given prefix

    Args:
        bucket_name: Name of the GCS bucket
        prefix: Prefix to filter blobs
        project_id: GCP project ID. If None, uses default from environment

    Returns:
        List of blob names matching the prefix
    """
    # Initialize the GCS client
    if project_id:
        client = storage.Client(project=project_id)
    else:
        client = storage.Client()

    bucket = client.bucket(bucket_name)
    blobs = bucket.list_blobs(prefix=prefix)

    return [blob.name for blob in blobs]


def gemini_batch(
    prompts: Dict[str, str],
    model: str = "gemini-2.5-flash",
    temperature: float = 0.2,
    gcs_bucket: Optional[str] = None,
    project_id: Optional[str] = None,
    location: str = "us-central1",
    thinking_budget: int = 0,
) -> dict[str, str]:
    """Runs a batch of prompts through the Gemini API

    Args:
        prompts: A dictionary {prompt_id: prompt} of prompts to run through the Gemini API
        model: The model to use for the Gemini API
        temperature: The temperature to use for the Gemini API
        gcs_bucket: GCS bucket name to upload files to (required for Vertex AI batch API)
        project_id: GCP project ID for GCS operations
        location: Google Cloud region for Vertex AI (default: us-central1)

    Returns:
        A dictionary {prompt_id: response} of responses from the Gemini API
    """
    if not gcs_bucket:
        raise ValueError("gcs_bucket is required for Vertex AI batch processing")

    if not project_id:
        raise ValueError("project_id is required for Vertex AI batch processing")

    # Set the Google Cloud project environment variable
    os.environ["GOOGLE_CLOUD_PROJECT"] = project_id

    # Initialize the Gemini client for Vertex AI with project and location
    client = genai.Client(
        http_options=HttpOptions(api_version="v1"),
        vertexai=True,
        project=project_id,
        location=location,
    )

    # Create unique timestamp for this batch
    timestamp = int(time.time())

    # Create a temporary directory for batch files
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        input_file = temp_path / "batch_input.jsonl"

        # Prepare the batch input file in JSONL format
        requests = "\n".join(
            [
                _create_batch_request(
                    prompt_id, prompt_text, temperature, thinking_budget
                )
                for prompt_id, prompt_text in prompts.items()
            ]
        )
        input_file.write_text(requests)

        # Upload input file to GCS
        input_blob_name = f"batch_input_{timestamp}.jsonl"
        src_uri = _upload_to_gcs(
            str(input_file),
            gcs_bucket,
            input_blob_name,
            project_id,
        )

        # Set up GCS output destination
        output_prefix = f"batch_output_{timestamp}"
        dest_uri = f"gs://{gcs_bucket}/{output_prefix}/"

        print(f"Input uploaded to: {src_uri}")
        print(f"Output will be written to: {dest_uri}")

        # Create batch job
        job = client.batches.create(
            model=model,
            src=src_uri,
            config=CreateBatchJobConfig(dest=dest_uri),
        )

        print(f"Batch job created: {job.name}")
        print(f"Initial state: {job.state}")

        # Wait for job completion
        completed_states = {
            JobState.JOB_STATE_SUCCEEDED,
            JobState.JOB_STATE_FAILED,
            JobState.JOB_STATE_CANCELLED,
            JobState.JOB_STATE_PAUSED,
        }

        while job.state not in completed_states:
            print(f"Job state: {job.state}, waiting...")
            time.sleep(10)  # Check every 10 seconds
            job = client.batches.get(name=job.name)

        print(f"Final job state: {job.state}")

        if job.state != JobState.JOB_STATE_SUCCEEDED:
            raise RuntimeError(f"Batch job failed with state: {job.state}")

        # List and download output files from GCS
        output_blobs = _list_gcs_blobs(gcs_bucket, output_prefix, project_id)

        if not output_blobs:
            raise RuntimeError(f"No output files found with prefix: {output_prefix}")

        print(f"Found {len(output_blobs)} output files")

        # Process batch results
        results = {}

        for blob_name in output_blobs:
            if blob_name.endswith(".jsonl"):
                # Download the output file
                output_file = temp_path / f"output_{blob_name.split('/')[-1]}"
                gcs_output_uri = f"gs://{gcs_bucket}/{blob_name}"

                print(f"Downloading: {gcs_output_uri}")
                _download_from_gcs(gcs_output_uri, str(output_file), project_id)

                # Process the downloaded file
                with open(output_file, "r") as f:
                    for line in f:
                        if line.strip():
                            custom_id, response_text = _parse_result_line(line)
                            if custom_id and custom_id in prompts:
                                results[custom_id] = response_text

        # Ensure all prompts have a result (even if empty)
        for prompt_id in prompts.keys():
            if prompt_id not in results:
                results[prompt_id] = ""

        print(f"Successfully processed {len(results)} results")
        return results, job
