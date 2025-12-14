"""Script to generate the OpenAPI client from the FastAPI service."""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def generate_client(openapi_url: str | None = None) -> None:
    """Generate the OpenAPI client from the FastAPI service.

    Args:
        openapi_url: URL to the OpenAPI specification. If None, will use
            environment variable OPENAPI_URL or default to localhost:8000.

    """
    if openapi_url is None:
        openapi_url = os.getenv("OPENAPI_URL", "http://localhost:8000/openapi.json")

    output_dir = Path(__file__).parent.parent / "src" / "openai_client_service_api_client"

    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        "-m",
        "openapi_python_client",
        "generate",
        openapi_url,
        "--output-path",
        str(output_dir),
        "--package-name",
        "openai_client_service_api_client",
        "--meta=none",
    ]

    try:
        subprocess.run(cmd, check=True)  # noqa: S603
    except subprocess.CalledProcessError:
        sys.exit(1)
    except FileNotFoundError:
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate OpenAPI client from the FastAPI service",
    )
    parser.add_argument(
        "--url",
        help="URL to the OpenAPI specification (default: http://localhost:8000/openapi.json)",
        default=None,
    )
    args = parser.parse_args()
    generate_client(args.url)
