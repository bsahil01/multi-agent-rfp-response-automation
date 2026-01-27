import json
import os
from typing import List, Dict, Any
from datetime import datetime, timedelta
from langchain.tools import tool


def load_mock_rfps() -> List[Dict[str, Any]]:
    """Load mock RFPs from JSON file"""
    # Try multiple paths to find the mock data
    possible_paths = [
        # From tools.py location: go up 3 levels to project root
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data', 'mock_rfps.json'),
        # From current working directory
        os.path.join(os.getcwd(), 'data', 'mock_rfps.json'),
        # Relative path
        'data/mock_rfps.json',
    ]

    for json_path in possible_paths:
        try:
            with open(json_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            continue

    return []


@tool
def scan_rfps_tool(keywords: List[str], days_ahead: int = 90) -> List[Dict[str, Any]]:
    """Scan for RFPs matching keywords and due within specified timeframe"""
    mock_rfps = load_mock_rfps()
    
    if not mock_rfps:
        return []
    
    keywords_lower = [k.lower() for k in keywords]
    filtered_rfps = []
    for rfp in mock_rfps:
        matches = any(
            keyword in str(rfp.get('title', '')).lower() or
            keyword in str(rfp.get('description', '')).lower() or
            keyword in str(rfp.get('category', '')).lower()
            for keyword in keywords_lower
        )
        if matches:
            filtered_rfps.append(rfp)
    
    cutoff_date = datetime.now() + timedelta(days=days_ahead)
    date_filtered_rfps = []
    for rfp in filtered_rfps:
        try:
            due_date = datetime.strptime(rfp['due_date'], "%Y-%m-%d")
            if due_date <= cutoff_date:
                days_remaining = (due_date - datetime.now()).days
                rfp['days_remaining'] = max(days_remaining, 0)
                date_filtered_rfps.append(rfp)
        except (KeyError, ValueError):
            continue
    
    return date_filtered_rfps


@tool
def qualify_rfp_tool(rfp: Dict[str, Any], criteria: Dict[str, Any]) -> Dict[str, Any]:
    """Qualify an RFP based on business criteria and assign a score"""
    qualification = {
        "rfp_id": rfp['rfp_id'],
        "qualified": True,
        "score": 0,
        "reasons": []
    }
    
    days_remaining = rfp.get('days_remaining', 0)
    min_days = criteria.get('min_days_remaining', 7)
    
    if days_remaining < min_days:
        qualification['qualified'] = False
        qualification['reasons'].append(f"Insufficient time: {days_remaining} days (need {min_days}+)")
    elif days_remaining < 14:
        qualification['score'] += 15
        qualification['reasons'].append(f"Tight timeline: {days_remaining} days")
    elif days_remaining < 30:
        qualification['score'] += 25
        qualification['reasons'].append(f"Adequate time: {days_remaining} days")
    else:
        qualification['score'] += 30
        qualification['reasons'].append(f"Good timeline: {days_remaining} days")
    
    tender_value = int(rfp.get('tender_value', 0))
    min_value = criteria.get('min_tender_value', 1000000)
    
    if tender_value < min_value:
        qualification['score'] += 10
        qualification['reasons'].append(f"Low value: ₹{tender_value:,}")
    elif tender_value < min_value * 2:
        qualification['score'] += 25
        qualification['reasons'].append(f"Meets minimum: ₹{tender_value:,}")
    elif tender_value < min_value * 5:
        qualification['score'] += 35
        qualification['reasons'].append(f"Good value: ₹{tender_value:,}")
    else:
        qualification['score'] += 40
        qualification['reasons'].append(f"High value: ₹{tender_value:,}")
    
    preferred_locations = criteria.get('preferred_locations', [])
    if not preferred_locations:
        qualification['score'] += 30
        qualification['reasons'].append(f"Location: {rfp.get('location', 'N/A')}")
    else:
        location_match = any(loc.lower() in str(rfp.get('location', '')).lower() for loc in preferred_locations)
        if location_match:
            qualification['score'] += 30
            qualification['reasons'].append(f"Preferred location: {rfp.get('location')}")
        else:
            qualification['score'] += 10
            qualification['reasons'].append(f"Non-preferred location: {rfp.get('location')}")
    
    qualification['qualified'] = qualification['score'] >= 60
    
    return qualification


@tool
def prioritize_rfps_tool(rfps: List[Dict[str, Any]], qualifications: List[Dict[str, Any]], top_n: int = 5) -> List[Dict[str, Any]]:
    """Prioritize qualified RFPs and return top N"""
    qual_lookup = {q['rfp_id']: q for q in qualifications}
    
    scored_rfps = []
    for rfp in rfps:
        qual = qual_lookup.get(rfp['rfp_id'])
        if qual and qual['qualified']:
            rfp['priority_score'] = qual['score']
            rfp['qualification'] = qual
            scored_rfps.append(rfp)
    
    scored_rfps.sort(key=lambda x: x['priority_score'], reverse=True)
    
    return scored_rfps[:top_n]
