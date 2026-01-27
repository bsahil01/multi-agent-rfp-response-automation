import json
import os
from typing import Dict, Any, List, Tuple


def load_test_pricing() -> Dict[str, int]:
    """Load test pricing data from JSON."""
    possible_paths = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "test_pricing.json"),
        os.path.join(os.getcwd(), "data", "test_pricing.json"),
        "data/test_pricing.json",
    ]

    for json_path in possible_paths:
        try:
            with open(json_path, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            continue

    return {}


def recommend_tests(selected_rfp: Dict[str, Any], pricing_db: Dict[str, int]) -> List[str]:
    """Recommend tests based on RFP content."""
    text = f"{selected_rfp.get('title', '')} {selected_rfp.get('description', '')}".lower()
    tests = []

    if any(term in text for term in ["high voltage", "hv", "33kv", "11kv", "kv"]):
        tests.extend(["High Voltage Test", "Impulse Voltage Test"])

    if "underground" in text:
        tests.append("Water Penetration Test")

    tests.extend(["Mechanical Test", "Partial Discharge Test"])

    seen = set()
    filtered = []
    for test in tests:
        if test in pricing_db and test not in seen:
            filtered.append(test)
            seen.add(test)

    return filtered


def calculate_testing_cost(recommended_tests: List[str], pricing_db: Dict[str, int]) -> int:
    """Calculate total testing cost from pricing table."""
    return int(sum(pricing_db.get(test, 0) for test in recommended_tests))


def calculate_material_cost(recommended_products: List[Dict[str, Any]], length_km: float = 1.0) -> float:
    """Calculate material cost from top recommendation and assumed length."""
    if not recommended_products:
        return 0.0

    primary = recommended_products[0]
    price_per_km = primary.get("price_per_km") or 0
    try:
        return float(price_per_km) * float(length_km)
    except (TypeError, ValueError):
        return 0.0


def calculate_pricing_breakdown(material_cost: float, testing_cost: float, overhead_pct: float = 0.05, contingency_pct: float = 0.03) -> Tuple[float, float, float, float]:
    """Return (overhead, contingency, subtotal, grand_total)."""
    subtotal = material_cost + testing_cost
    overhead = round(subtotal * overhead_pct, 2)
    contingency = round(subtotal * contingency_pct, 2)
    grand_total = round(subtotal + overhead + contingency, 2)
    return overhead, contingency, subtotal, grand_total
