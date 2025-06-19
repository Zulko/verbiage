import time
import json
import tempfile
from pathlib import Path
from typing import Dict, Optional
from google import genai
from google.genai.types import CreateBatchJobConfig, JobState, HttpOptions


def gemini_batch(
    prompts: Dict[str, str], model: str = "gemini-2.5-flash", temperature: float = 0.2
) -> dict[str, str]:
    """Runs a batch of prompt through the Gemini API

    Args:
        prompts: A dictionary {prompt_id: prompt} of prompts to run through the Gemini API
        model: The model to use for the Gemini API
        temperature: The temperature to use for the Gemini API

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
        with open(input_file, "w") as f:
            for prompt_id, prompt_text in prompts.items():
                request = {
                    "request": {
                        "contents": [
                            {"role": "user", "parts": [{"text": prompt_text}]}
                        ],
                        "generationConfig": {
                            "temperature": temperature,
                            "responseMimeType": "text/plain",
                        },
                    }
                }
                # Add prompt_id as metadata to track responses
                request["custom_id"] = prompt_id
                f.write(json.dumps(request) + "\n")

        # Create batch job
        job = client.batches.create(
            model=model,
            src=str(input_file),
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
            time.sleep(30)  # Check every 30 seconds
            job = client.batches.get(name=job.name)

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
                        try:
                            result = json.loads(line)
                            custom_id = result.get("custom_id")
                            if custom_id and custom_id in prompts:
                                # Extract the response text from the result
                                response_text = ""
                                if "response" in result:
                                    candidates = result["response"].get(
                                        "candidates", []
                                    )
                                    if candidates and len(candidates) > 0:
                                        content = candidates[0].get("content", {})
                                        parts = content.get("parts", [])
                                        if parts and len(parts) > 0:
                                            response_text = parts[0].get("text", "")

                                results[custom_id] = response_text
                        except json.JSONDecodeError:
                            continue

        # Ensure all prompts have a result (even if empty)
        for prompt_id in prompts.keys():
            if prompt_id not in results:
                results[prompt_id] = ""

        return results
