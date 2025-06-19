import time
import json
import tempfile
from pathlib import Path
from typing import Dict, Optional
from google import genai
from google.genai.types import CreateBatchJobConfig, JobState, HttpOptions
from google.cloud import storage


def _create_batch_request(prompt_id: str, prompt_text: str, temperature: float) -> Dict:
    """Create a single batch request object for the Gemini API

    Args:
        prompt_id: Unique identifier for this prompt
        prompt_text: The actual prompt text
        temperature: Temperature setting for generation

    Returns:
        Dictionary containing the formatted request for the batch API
    """
    return json.dumps(
        {
            "custom_id": prompt_id,
            "request": {
                "contents": [{"role": "user", "parts": [{"text": prompt_text}]}],
                "generationConfig": {
                    "temperature": temperature,
                    "responseMimeType": "text/plain",
                },
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


def gemini_batch(
    prompts: Dict[str, str],
    model: str = "gemini-2.5-flash",
    temperature: float = 0.2,
    gcs_bucket: Optional[str] = None,
    project_id: Optional[str] = None,
) -> dict[str, str]:
    """Runs a batch of prompt through the Gemini API

    Args:
        prompts: A dictionary {prompt_id: prompt} of prompts to run through the Gemini API
        model: The model to use for the Gemini API
        temperature: The temperature to use for the Gemini API
        gcs_bucket: Optional GCS bucket name to upload the input file to
        project_id: Optional GCP project ID for GCS operations

    Returns:
        A dictionary {prompt_id: response} of responses from the Gemini API
    """
    # Initialize the Gemini client for Vertex AI
    client = genai.Client(http_options=HttpOptions(api_version="v1"), vertexai=True)

    # Create a temporary directory for batch files
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        input_file = temp_path / "batch_input.jsonl"
        output_dir = temp_path / "output"

        # Prepare the batch input file in JSONL format
        requests = "\n".join(
            [
                json.dumps(_create_batch_request(prompt_id, prompt_text, temperature))
                for prompt_id, prompt_text in prompts.items()
            ]
        )
        input_file.write_text(requests)

        # Determine the source file path/URI
        if gcs_bucket:
            # Upload to GCS and use the GCS URI
            src_uri = _upload_to_gcs(
                str(input_file),
                gcs_bucket,
                f"batch_input_{int(time.time())}.jsonl",
                project_id,
            )
        else:
            # Use local file path
            src_uri = str(input_file)

        # Create batch job
        job = client.batches.create(
            model=model,
            src=src_uri,
            config=CreateBatchJobConfig(dest=str(output_dir)),
        )

        # Wait for job completion
        completed_states = {
            JobState.JOB_STATE_SUCCEEDED,
            JobState.JOB_STATE_FAILED,
            JobState.JOB_STATE_CANCELLED,
            JobState.JOB_STATE_PAUSED,
        }

        while job.state not in completed_states:
            time.sleep(10)  # Check every 10 seconds
            job = client.batches.get(name=job.name)
            print(job)

        if job.state != JobState.JOB_STATE_SUCCEEDED:
            raise RuntimeError(f"Batch job failed with state: {job.state}")

        # Process batch results
        results = {}

        # Find the output file(s) in the output directory
        output_files = list(output_dir.glob("*.jsonl"))
        if not output_files:
            # If no local files, try to get results from the job object
            # This might require different handling depending on the actual API response
            return {
                prompt_id: f"No output found for batch job {job.name}"
                for prompt_id in prompts.keys()
            }

        # Read and process the output file(s)
        for output_file in output_files:
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

        return results
