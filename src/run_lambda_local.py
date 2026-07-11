"""Run the Lambda handler locally with a simulated EventBridge event."""

import json
from pathlib import Path
from typing import Any

from stockpipeline.ingestion.lambda_function import lambda_handler


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EVENT_FILE = (
    PROJECT_ROOT
    / "sample-data"
    / "eventbridge-scheduled-event.json"
)


class LocalLambdaContext:
    """Minimal Lambda context object for local testing."""

    aws_request_id = "local-request-001"
    function_name = "stock-pipeline-ingestion-local"
    memory_limit_in_mb = 128


def load_event() -> dict[str, Any]:
    """Load the simulated EventBridge event."""
    with EVENT_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def main() -> None:
    """Invoke the Lambda handler locally."""
    event = load_event()
    context = LocalLambdaContext()

    response = lambda_handler(
        event=event,
        context=context,
    )

    print(
        json.dumps(
            response,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()