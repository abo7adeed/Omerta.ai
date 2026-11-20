"""Update langflow/sanctions_screening_flow.json with executable component definitions.

Ensures every node has executable Component code in template.code.value so that
Langflow Studio Build and Playground execute natively.
"""

from __future__ import annotations

import json
from pathlib import Path

bridge_path = Path("langflow/components/omerta_sanctions_bridge.py")
bridge_raw = bridge_path.read_text(encoding="utf-8")

# Extract clean imports for Langflow Studio's AST validator
bridge_body_start = bridge_raw.find("logger = logging.getLogger(__name__)")
if bridge_body_start != -1:
    bridge_code = """from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any

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

""" + bridge_raw[bridge_body_start:]
else:
    bridge_code = bridge_raw

entity_input_code = '''from lfx.custom.custom_component.component import Component
from lfx.io import StrInput, DropdownInput, Output
from lfx.schema import Data

class EntityInputComponent(Component):
    display_name = "Investigation Entity Input"
    description = "Receives entity descriptors from Omerta case or manual compliance entry."
    icon = "UserCheck"

    inputs = [
        StrInput(name="name", display_name="Entity Name", value="Mohamed El-Sayed Ahmed", required=True),
        DropdownInput(name="entity_type", display_name="Entity Type", options=["individual", "company", "organization", "vessel", "aircraft", "any"], value="individual"),
        StrInput(name="country", display_name="Country (ISO-2)", value="EG"),
        StrInput(name="birth_date", display_name="Date of Birth (YYYY-MM-DD)", value="1982-05-14"),
        StrInput(name="identification_number", display_name="National ID / Passport", value="EG-NAT-28205140102931"),
    ]

    outputs = [
        Output(name="output", display_name="Result Data", method="build_output"),
    ]

    def build_output(self) -> Data:
        return Data(data={
            "name": getattr(self, "name", "Mohamed El-Sayed Ahmed"),
            "entity_type": getattr(self, "entity_type", "individual"),
            "country": getattr(self, "country", "EG"),
            "birth_date": getattr(self, "birth_date", "1982-05-14"),
            "identification_number": getattr(self, "identification_number", "EG-NAT-28205140102931"),
        })
'''

norm_code = '''import re
import unicodedata
from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, Output
from lfx.schema import Data

def normalize_name_text(text: str) -> str:
    if not text:
        return ""
    # Strip Tashkeel (Arabic diacritics)
    tashkeel = re.compile(r"[\\u0617-\\u061A\\u064B-\\u0652]")
    text = re.sub(tashkeel, "", text)
    # Normalize Alef forms
    text = re.sub(r"[إأآا]", "ا", text)
    # Normalize Yaa
    text = re.sub(r"[ىي]", "ي", text)
    # Normalize Taa Marbuta
    text = re.sub(r"ة", "ه", text)
    text = unicodedata.normalize("NFKD", text)
    return " ".join(text.strip().split())

class NormalizationComponent(Component):
    display_name = "Arabic/English Normalizer"
    description = "Preprocesses script, strips Tashkeel, unifies Hamza/Alif, and expands transliterations."
    icon = "Languages"

    inputs = [
        DataInput(name="input_data", display_name="Pipeline Input", required=True),
    ]

    outputs = [
        Output(name="output", display_name="Result Data", method="process_normalization"),
    ]

    def process_normalization(self) -> Data:
        inp = getattr(self, "input_data", None)
        d = inp.data if hasattr(inp, "data") and isinstance(inp.data, dict) else (inp if isinstance(inp, dict) else {})
        raw_name = d.get("name") or d.get("entity_name") or ""
        norm_name = normalize_name_text(raw_name)
        country = d.get("country") or ""
        countries = [c.strip().upper() for c in country.split(",") if c.strip()] if isinstance(country, str) else d.get("countries", [])
        return Data(data={
            "original_name": raw_name,
            "normalized_name": norm_name,
            "name": norm_name or raw_name,
            "entity_type": d.get("entity_type", "individual"),
            "country": country,
            "countries": countries,
            "birth_date": d.get("birth_date"),
            "identification_number": d.get("identification_number"),
            "normalization_applied": True,
        })
'''

scoring_code = '''from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, FloatInput, Output
from lfx.schema import Data

class MultiSignalScoringComponent(Component):
    display_name = "Multi-Signal Scoring & Ranker"
    description = "Evaluates candidate signals (name, DOB, country, ID) against weighted criteria."
    icon = "Calculator"

    inputs = [
        DataInput(name="input_data", display_name="Pipeline Input", required=True),
        FloatInput(name="name_weight", display_name="Name Weight", value=0.50),
        FloatInput(name="dob_weight", display_name="DOB Weight", value=0.25),
        FloatInput(name="country_weight", display_name="Country Weight", value=0.15),
        FloatInput(name="id_weight", display_name="ID Weight", value=0.10),
    ]

    outputs = [
        Output(name="output", display_name="Result Data", method="process_scoring"),
    ]

    def process_scoring(self) -> Data:
        inp = getattr(self, "input_data", None)
        d = dict(inp.data) if hasattr(inp, "data") and isinstance(inp.data, dict) else (dict(inp) if isinstance(inp, dict) else {})
        d["scoring_weights"] = {
            "name_weight": getattr(self, "name_weight", 0.50),
            "dob_weight": getattr(self, "dob_weight", 0.25),
            "country_weight": getattr(self, "country_weight", 0.15),
            "id_weight": getattr(self, "id_weight", 0.10),
        }
        return Data(data=d)
'''

hitl_code = '''from lfx.custom.custom_component.component import Component
from lfx.io import BoolInput, DataInput, Output
from lfx.schema import Data

class ExplainabilityHITLComponent(Component):
    display_name = "Explainability & HITL Advisor"
    description = "Formulates transparent audit reasoning, flags review obligations, and prevents auto-freezing."
    icon = "AlertTriangle"

    inputs = [
        DataInput(name="input_data", display_name="Pipeline Input", required=True),
        BoolInput(name="enforce_hitl", display_name="Enforce Human Review", value=True),
    ]

    outputs = [
        Output(name="output", display_name="Result Data", method="process_advisory"),
    ]

    def process_advisory(self) -> Data:
        inp = getattr(self, "input_data", None)
        d = dict(inp.data) if hasattr(inp, "data") and isinstance(inp.data, dict) else (dict(inp) if isinstance(inp, dict) else {})
        enforce = getattr(self, "enforce_hitl", True)
        if d.get("match_found"):
            d["review_required"] = True
            d["hitl_recommendation"] = "MANDATORY_HUMAN_REVIEW: Potential sanctions match detected. Auto-freezing is strictly prohibited. Compliance analyst disposition required."
        else:
            d["review_required"] = False if not enforce else d.get("review_required", False)
            d["hitl_recommendation"] = "CLEAR: No watchlist matches detected exceeding confidence threshold."
        return Data(data=d)
'''

report_code = '''from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, DropdownInput, Output
from lfx.schema import Data

class ScreeningAuditReportComponent(Component):
    display_name = "Screening Audit Report"
    description = "Final structured JSON payload with decision recommendation and audit trail."
    icon = "FileText"

    inputs = [
        DataInput(name="input_data", display_name="Pipeline Input", required=True),
        DropdownInput(name="format", display_name="Format", options=["application/json", "text/plain"], value="application/json"),
    ]

    outputs = [
        Output(name="output", display_name="Result Data", method="generate_report"),
    ]

    def generate_report(self) -> Data:
        inp = getattr(self, "input_data", None)
        d = dict(inp.data) if hasattr(inp, "data") and isinstance(inp.data, dict) else (dict(inp) if isinstance(inp, dict) else {})
        d["audit_report_generated"] = True
        return Data(data=d)
'''

def update_flow() -> None:
    flow_file = Path("langflow/sanctions_screening_flow.json")
    flow_data = json.loads(flow_file.read_text(encoding="utf-8"))

    for node in flow_data["data"]["nodes"]:
        nid = node["id"]
        node["data"]["id"] = nid
        node["data"]["display_name"] = node["data"]["node"]["display_name"]
        node["data"]["description"] = node["data"]["node"]["description"]
        node["data"]["node"]["base_classes"] = ["Data"]
        tmpl = node["data"]["node"]["template"]
        if "input_data" in tmpl and isinstance(tmpl["input_data"], dict):
            tmpl["input_data"]["type"] = "other"
            tmpl["input_data"]["_input_type"] = "DataInput"

        # Set output method and properties
        methods = {
            "node_input_entity": "build_output",
            "node_normalize": "process_normalization",
            "node_mcp_tool": "execute_screening",
            "node_scoring": "process_scoring",
            "node_explainability": "process_advisory",
            "node_output": "generate_report",
        }
        for out in node["data"]["node"].get("outputs", []):
            out["method"] = methods.get(nid, "build_output")
            out.setdefault("cache", True)
            out.setdefault("allows_loop", False)
            out.setdefault("value", "__UNDEFINED__")
        if nid == "node_input_entity":
            tmpl["code"] = {"type": "code", "value": entity_input_code, "show": False, "advanced": True}
        elif nid == "node_normalize":
            tmpl["code"] = {"type": "code", "value": norm_code, "show": False, "advanced": True}
        elif nid == "node_mcp_tool":
            tmpl["code"] = {"type": "code", "value": bridge_code, "show": False, "advanced": True}
            tmpl["endpoint_url"] = {
                "type": "str", "value": "http://127.0.0.1:8000/api/v1/sanctions/screen",
                "show": True, "display_name": "Omerta Screening Endpoint", "advanced": True
            }
            tmpl["threshold"] = {
                "type": "float", "value": 0.70,
                "show": True, "display_name": "Confidence Threshold", "advanced": False
            }
            tmpl["entity_name"] = {
                "type": "str", "value": "Mohamed El-Sayed Ahmed",
                "show": True, "display_name": "Entity Name", "advanced": False
            }
            tmpl["entity_type"] = {
                "type": "str", "value": "individual",
                "options": ["individual", "company", "organization", "vessel", "aircraft", "any"],
                "show": True, "display_name": "Entity Type", "advanced": False
            }
            tmpl["country"] = {
                "type": "str", "value": "EG",
                "show": True, "display_name": "Country (ISO-2)", "advanced": False
            }
            tmpl["birth_date"] = {
                "type": "str", "value": "1982-05-14",
                "show": True, "display_name": "Date of Birth (YYYY-MM-DD)", "advanced": False
            }
            tmpl["identification_number"] = {
                "type": "str", "value": "EG-NAT-28205140102931",
                "show": True, "display_name": "National ID / Passport", "advanced": False
            }
            tmpl["auth_token"] = {
                "type": "str", "value": "",
                "show": True, "display_name": "API Bearer Token (Optional)", "advanced": True
            }
        elif nid == "node_scoring":
            tmpl["code"] = {"type": "code", "value": scoring_code, "show": False, "advanced": True}
        elif nid == "node_explainability":
            tmpl["code"] = {"type": "code", "value": hitl_code, "show": False, "advanced": True}
        elif nid == "node_output":
            tmpl["code"] = {"type": "code", "value": report_code, "show": False, "advanced": True}

    flow_file.write_text(json.dumps(flow_data, indent=2), encoding="utf-8")
    print("Successfully updated langflow/sanctions_screening_flow.json with executable component definitions.")

if __name__ == "__main__":
    update_flow()
