"""Langflow Standalone Execution Bridge Component: Omerta Sanctions Screening.

Enables Langflow Studio's Build and Playground interfaces to execute real-time
watchlist screening by bridging to the authoritative Omerta FastAPI gateway and
the underlying read-only Sanctions MCP tool.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any

try:
    from lfx.custom.custom_component.component import Component
    from lfx.io import (
        DataInput,
        DropdownInput,
        FloatInput,
        Output,
        SecretStrInput,
        StrInput,
    )
    from lfx.schema import Data
except ImportError:
    try:
        from langflow.custom import Component
        from langflow.io import (
            DataInput,
            DropdownInput,
            FloatInput,
            Output,
            SecretStrInput,
            StrInput,
        )
        from langflow.schema import Data
    except ImportError:
        # Fallback base class if executed in unit tests where Langflow is managed by uvx
        class Component:  # type: ignore[no-redef]
            inputs: list[Any] = []
            outputs: list[Any] = []
            display_name: str = ""
            description: str = ""

            def __init__(self, **kwargs: Any) -> None:
                for k, v in kwargs.items():
                    setattr(self, k, v)

            def set_attributes(self, attrs: dict[str, Any]) -> None:
                for k, v in attrs.items():
                    setattr(self, k, v)

        class Data:  # type: ignore[no-redef]
            def __init__(self, data: dict[str, Any]) -> None:
                self.data = data

        class StrInput:  # type: ignore[no-redef]
            def __init__(self, **kwargs: Any) -> None:
                pass

        class DropdownInput:  # type: ignore[no-redef]
            def __init__(self, **kwargs: Any) -> None:
                pass

        class FloatInput:  # type: ignore[no-redef]
            def __init__(self, **kwargs: Any) -> None:
                pass

        class SecretStrInput:  # type: ignore[no-redef]
            def __init__(self, **kwargs: Any) -> None:
                pass

        class DataInput:  # type: ignore[no-redef]
            def __init__(self, **kwargs: Any) -> None:
                pass

        class Output:  # type: ignore[no-redef]
            def __init__(self, **kwargs: Any) -> None:
                pass

logger = logging.getLogger(__name__)

DEFAULT_OMERTA_URL = os.getenv("OMERTA_API_URL", "http://127.0.0.1:8000/api/v1/sanctions/screen")


class OmertaSanctionsBridgeComponent(Component):
    """Bridge component triggering Omerta sanctions screening MCP tools from Langflow."""

    display_name = "Omerta Sanctions Screening Bridge"
    description = (
        "Invokes Omerta.ai sanctions screening via authenticated FastAPI gateway and "
        "omerta-sanctions-server MCP tool. Returns multi-signal explainable match scoring."
    )
    icon = "ShieldCheck"

    inputs = [
        DataInput(
            name="input_data",
            display_name="Pipeline Input Data",
            info="Optional input data from upstream normalization or entity node.",
            required=False,
        ),
        StrInput(
            name="entity_name",
            display_name="Entity Name",
            info="Full name or alias of the individual or company to screen.",
            value="Mohamed El-Sayed Ahmed",
            required=False,
        ),
        DropdownInput(
            name="entity_type",
            display_name="Entity Type",
            options=["individual", "company", "organization", "vessel", "aircraft", "any"],
            value="individual",
            info="Type of entity.",
        ),
        StrInput(
            name="country",
            display_name="Country (ISO-2)",
            value="EG",
            info="ISO 2-letter country code (e.g. EG, US, RU). Comma-separate for multiple.",
        ),
        StrInput(
            name="birth_date",
            display_name="Date of Birth (YYYY-MM-DD)",
            value="1982-05-14",
            info="Date of birth for individuals (e.g. 1982-05-14).",
        ),
        StrInput(
            name="identification_number",
            display_name="National ID / Passport",
            value="EG-NAT-28205140102931",
            info="Government identification number, tax ID, or passport number.",
        ),
        FloatInput(
            name="threshold",
            display_name="Confidence Threshold",
            value=0.70,
            info="Minimum confidence score required to flag a potential sanctions match (0.10 to 1.00).",
        ),
        StrInput(
            name="endpoint_url",
            display_name="Omerta Screening Endpoint",
            value=DEFAULT_OMERTA_URL,
            info="URL of the Omerta FastAPI sanctions screening endpoint.",
            advanced=True,
        ),
        SecretStrInput(
            name="auth_token",
            display_name="API Bearer Token (Optional)",
            value="",
            info="JWT access token for authenticated environments. Reads OMERTA_BEARER_TOKEN if empty.",
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            name="output",
            display_name="Result Data",
            method="execute_screening",
        ),
        Output(
            name="screening_result",
            display_name="Screening Result (Data)",
            method="execute_screening",
        ),
    ]

    def execute_screening(self) -> Data:
        """Execute the screening operation via the Omerta backend and MCP tool."""
        # 1. Inspect upstream input_data if provided
        upstream = {}
        input_data_obj = getattr(self, "input_data", None)
        if input_data_obj is not None:
            if hasattr(input_data_obj, "data") and isinstance(input_data_obj.data, dict):
                upstream = input_data_obj.data
            elif isinstance(input_data_obj, dict):
                upstream = input_data_obj

        # 2. Resolve fields (direct attributes take precedence over upstream defaults)
        raw_name = getattr(self, "entity_name", "") or upstream.get("name") or upstream.get("original_name") or upstream.get("entity_name") or ""
        if not raw_name or not str(raw_name).strip():
            err_payload = {
                "match_found": False,
                "best_match_confidence": 0.0,
                "review_required": False,
                "error": "INVALID_INPUT",
                "detail": "Entity name is required and cannot be empty.",
                "status": "ERROR",
            }
            return Data(data=err_payload)

        name = str(raw_name).strip()
        entity_type = getattr(self, "entity_type", "") or upstream.get("entity_type") or "individual"
        country_str = getattr(self, "country", "") or upstream.get("country") or ""
        birth_date = getattr(self, "birth_date", None) or upstream.get("birth_date")
        id_number = getattr(self, "identification_number", None) or upstream.get("identification_number")
        threshold_val = getattr(self, "threshold", 0.70)
        endpoint = getattr(self, "endpoint_url", DEFAULT_OMERTA_URL) or DEFAULT_OMERTA_URL
        token = getattr(self, "auth_token", "") or os.getenv("OMERTA_BEARER_TOKEN", "")

        if isinstance(country_str, list):
            countries = [c.strip().upper() for c in country_str if c and str(c).strip()]
        else:
            countries = [c.strip().upper() for c in str(country_str).split(",") if c.strip()]

        try:
            clamped_threshold = max(0.1, min(1.0, float(threshold_val)))
        except (ValueError, TypeError):
            clamped_threshold = 0.70

        payload = {
            "name": name,
            "entity_type": entity_type,
            "countries": countries,
            "birth_date": str(birth_date).strip() if birth_date else None,
            "identification_number": str(id_number).strip() if id_number else None,
            "threshold": clamped_threshold,
            "limit": 5,
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Langflow-Omerta-Bridge/1.0",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"

        req_body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(endpoint, data=req_body, headers=headers, method="POST")

        # 3. Dispatch HTTP Request to Omerta Backend
        try:
            with urllib.request.urlopen(request, timeout=30.0) as response:
                resp_code = response.status
                resp_text = response.read().decode("utf-8")
                data = json.loads(resp_text)

                # Ensure HITL invariant is preserved
                if data.get("match_found"):
                    data["review_required"] = True

                # Add Langflow Bridge execution telemetry
                data["_langflow_bridge"] = {
                    "executed": True,
                    "target_endpoint": endpoint,
                    "status_code": resp_code,
                    "provenance": data.get("execution_metadata", {}).get("source_queried", "UNKNOWN"),
                }
                return Data(data=data)

        except urllib.error.HTTPError as exc:
            err_body = exc.read().decode("utf-8")
            try:
                parsed_err = json.loads(err_body)
            except Exception:
                parsed_err = {"detail": err_body}

            err_data = {
                "match_found": False,
                "best_match_confidence": 0.0,
                "review_required": False,
                "error": f"HTTP_{exc.code}",
                "detail": parsed_err.get("detail", str(exc)),
                "status": "ERROR",
                "_langflow_bridge": {
                    "executed": False,
                    "target_endpoint": endpoint,
                    "status_code": exc.code,
                },
            }
            return Data(data=err_data)

        except (urllib.error.URLError, ConnectionRefusedError, OSError) as exc:
            err_data = {
                "match_found": False,
                "best_match_confidence": 0.0,
                "review_required": False,
                "error": "BACKEND_UNAVAILABLE",
                "detail": f"Failed to connect to Omerta FastAPI at {endpoint}: {exc.reason if hasattr(exc, 'reason') else exc}",
                "status": "ERROR",
                "_langflow_bridge": {
                    "executed": False,
                    "target_endpoint": endpoint,
                    "error_type": "ConnectionFailure",
                },
            }
            return Data(data=err_data)

        except TimeoutError as exc:
            err_data = {
                "match_found": False,
                "best_match_confidence": 0.0,
                "review_required": False,
                "error": "TIMEOUT",
                "detail": f"Request to Omerta FastAPI at {endpoint} timed out after 15 seconds.",
                "status": "ERROR",
                "_langflow_bridge": {
                    "executed": False,
                    "target_endpoint": endpoint,
                    "error_type": "Timeout",
                },
            }
            return Data(data=err_data)

        except Exception as exc:
            err_data = {
                "match_found": False,
                "best_match_confidence": 0.0,
                "review_required": False,
                "error": "UNEXPECTED_ERROR",
                "detail": str(exc),
                "status": "ERROR",
            }
            return Data(data=err_data)

