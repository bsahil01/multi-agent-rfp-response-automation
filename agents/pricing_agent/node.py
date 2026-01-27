import json
from typing import Dict, Any, List
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from state import AgentState, WorkflowStep, NodeName
from llm_config import get_shared_llm
from pricing_agent.tools import (
    load_test_pricing,
    recommend_tests,
    calculate_testing_cost,
    calculate_material_cost,
    calculate_pricing_breakdown,
)


PRICING_AGENT_PROMPT = """You are a Pricing Agent for a B2B electrical cable manufacturing company.

**Your Role**:
Generate a clear pricing summary for the selected RFP using available inputs.

**Output Format**:
- Use markdown formatting
- Provide a concise cost breakdown
- Highlight any assumptions
- Recommend next steps
"""


def pricing_agent_node(state: AgentState) -> Dict[str, Any]:
    """Generate pricing summary for selected RFP."""
    print("\n" + "="*60)
    print("💰 PRICING AGENT STARTED")
    print("="*60)
    
    llm = get_shared_llm()
    selected_rfp = state.get("selected_rfp")
    
    print(f"Selected RFP: {selected_rfp.get('rfp_id') if selected_rfp else 'None'}")

    if not selected_rfp:
        print("❌ No RFP selected!")
        return {
            "messages": [AIMessage(content="No RFP selected. Please select an RFP first.")],
            "next_node": NodeName.END,
            "current_step": WorkflowStep.ERROR
        }

    try:
        print("💵 Loading pricing data...")
        pricing_db = load_test_pricing()
        recommended_tests = recommend_tests(selected_rfp, pricing_db)
        testing_cost = calculate_testing_cost(recommended_tests, pricing_db)

        technical_analysis = state.get("technical_analysis") or {}
        recommended_products = technical_analysis.get("recommended_products", [])
        assumed_length_km = selected_rfp.get("length_km", 1.0)

        material_cost = round(calculate_material_cost(recommended_products, assumed_length_km), 2)
        overhead, contingency, subtotal, grand_total = calculate_pricing_breakdown(material_cost, testing_cost)

        pricing_summary = {
            "rfp_id": selected_rfp.get("rfp_id"),
            "assumed_length_km": assumed_length_km,
            "recommended_tests": recommended_tests,
            "testing_cost": testing_cost,
            "material_cost": material_cost,
            "overhead_pct": 0.05,
            "contingency_pct": 0.03,
            "overhead_cost": overhead,
            "contingency_cost": contingency,
            "subtotal": subtotal,
            "grand_total": grand_total,
        }

        # Only include essential technical data - not the full analysis text
        prompt = f"""
Selected RFP: {selected_rfp.get('rfp_id')} - {selected_rfp.get('title')}
Value: ₹{selected_rfp.get('value', 'N/A')}

Recommended Products (from Technical Agent):
{json.dumps(recommended_products, indent=2, default=str)}

Pricing Breakdown:
- Material Cost: ₹{material_cost:,.2f}
- Testing Cost: ₹{testing_cost:,.2f}
- Overhead (5%): ₹{overhead:,.2f}
- Contingency (3%): ₹{contingency:,.2f}
- **Grand Total: ₹{grand_total:,.2f}**

Provide a concise pricing summary with key assumptions and next steps.
"""

        messages = [
            SystemMessage(content=PRICING_AGENT_PROMPT),
            HumanMessage(content=prompt)
        ]

        print(f"🤖 Calling LLM for pricing analysis... (prompt size: {len(prompt)} chars)")
        try:
            response = llm.invoke(messages)
            print(f"📥 LLM response received ({len(response.content)} chars)")
        except Exception as llm_error:
            print(f"❌ LLM call failed: {str(llm_error)}")
            raise
        
        print(f"✅ Pricing analysis complete. Grand total: ₹{pricing_summary['grand_total']}")
        print(f"🔄 Routing to: {NodeName.MAIN_AGENT}")
        print("="*60 + "\n")

        return {
            "messages": [AIMessage(content=response.content)],
            "pricing_analysis": {"rfp_id": selected_rfp.get("rfp_id"), "analysis": response.content, "inputs": pricing_summary},
            "current_step": WorkflowStep.COMPLETE,
            "next_node": NodeName.MAIN_AGENT
        }

    except Exception as e:
        return {
            "messages": [AIMessage(content=f"Error generating pricing: {str(e)}")],
            "next_node": NodeName.END,
            "current_step": WorkflowStep.ERROR
        }
