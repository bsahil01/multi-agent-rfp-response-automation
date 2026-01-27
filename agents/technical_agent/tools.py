import json
import os
import re
from typing import Dict, Any, List, Optional


def build_technical_prompt(selected_rfp: dict) -> str:
    """Build the technical analysis prompt for the selected RFP."""
    rfp_data = json.dumps(selected_rfp, indent=2, default=str)

    return f"""
Analyze this RFP technically:

```json
{rfp_data}
```

Provide:
1. Technical requirements summary
2. Key specifications needed
3. Compliance requirements
4. Delivery feasibility
5. Risk assessment
6. Recommendation (bid / no-bid / need more info)
"""


def load_oem_catalog() -> List[Dict[str, Any]]:
    """Load OEM catalog from JSON."""
    possible_paths = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "catalog.json"),
        os.path.join(os.getcwd(), "data", "catalog.json"),
        "data/catalog.json",
    ]

    for json_path in possible_paths:
        try:
            with open(json_path, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            continue

    return []


def extract_requirements(text: str) -> Dict[str, Any]:
    """Extract basic cable requirements from free text."""
    text_lower = text.lower()

    voltage = None
    voltage_match = re.search(r"(\d+(\.\d+)?)\s*kv", text_lower)
    if voltage_match:
        voltage = f"{voltage_match.group(1)} kV"

    conductor = None
    if "copper" in text_lower:
        conductor = "Copper"
    elif "aluminium" in text_lower or "aluminum" in text_lower:
        conductor = "Aluminum"

    size = None
    size_match = re.search(r"(\d+)\s*(sq\.?mm|mm2|mm\^2)", text_lower)
    if size_match:
        size = f"{size_match.group(1)} sq.mm"

    insulation = None
    if "xlpe" in text_lower:
        insulation = "XLPE"
    elif "pvc" in text_lower:
        insulation = "PVC"
    elif "fr" in text_lower or "fr-lsh" in text_lower or "lszh" in text_lower:
        insulation = "FR"

    cores = None
    cores_match = re.search(r"(\d+)\s*core", text_lower)
    if cores_match:
        cores = int(cores_match.group(1))
    elif "single core" in text_lower:
        cores = 1
    elif "three core" in text_lower or "three-core" in text_lower:
        cores = 3

    armour = None
    if "armour" in text_lower or "armored" in text_lower or "armoured" in text_lower:
        if "steel tape" in text_lower:
            armour = "Steel Tape"
        elif "swa" in text_lower:
            armour = "SWA"
        else:
            armour = "GI Wire"

    cable_type = None
    if insulation:
        cable_type = insulation

    application = None
    if "underground" in text_lower:
        application = "Underground"
    elif "overhead" in text_lower:
        application = "Overhead"

    return {
        "voltage_rating": voltage,
        "conductor": conductor,
        "size": size,
        "cores": cores,
        "insulation": insulation,
        "armour": armour,
        "cable_type": cable_type,
        "application": application,
    }


SPEC_FIELDS = [
    "voltage_rating",
    "conductor",
    "size",
    "cores",
    "insulation",
    "armour",
    "cable_type",
    "application",
]


def normalize_value(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return str(value)
    return str(value).strip().lower()


def derive_product_field(specs: Dict[str, Any], field: str) -> Any:
    if field in specs:
        return specs.get(field)

    if field == "cable_type":
        return specs.get("insulation")
    if field == "application":
        return None
    return None


def score_catalog_product(product: Dict[str, Any], requirements: Dict[str, Any]) -> Dict[str, Any]:
    """Score a catalog product against extracted requirements (8 parameters, equal weight)."""
    specs = product.get("specifications", {})
    score = 0
    matched = {}
    comparisons = []

    for field in SPEC_FIELDS:
        req_value = requirements.get(field)
        spec_value = derive_product_field(specs, field)
        is_match = normalize_value(req_value) == normalize_value(spec_value) if req_value else False

        if is_match:
            score += 1
            matched[field] = spec_value

        comparisons.append({
            "field": field,
            "requirement": req_value,
            "product": spec_value,
            "match": is_match,
        })

    match_percent = round((score / len(SPEC_FIELDS)) * 100, 1)

    return {
        "sku": product.get("sku"),
        "product_name": product.get("product_name"),
        "price_per_km": product.get("price_per_km"),
        "specifications": specs,
        "match_score": match_percent,
        "matched_fields": matched,
        "comparison": comparisons,
    }


def match_oem_products(catalog: List[Dict[str, Any]], requirements: Dict[str, Any], top_n: int = 3) -> List[Dict[str, Any]]:
    """Return top N OEM products by match score."""
    scored = [score_catalog_product(product, requirements) for product in catalog]
    scored.sort(key=lambda x: x["match_score"], reverse=True)
    return scored[:top_n]


def build_comparison_table(recommendations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Build a comparison table across top recommendations."""
    rows = []
    for field in SPEC_FIELDS:
        row = {"field": field}
        for product in recommendations:
            row[product.get("sku", "unknown")] = product.get("specifications", {}).get(field) or \
                derive_product_field(product.get("specifications", {}), field)
        rows.append(row)
    return rows
