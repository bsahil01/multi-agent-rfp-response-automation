import json
from typing import Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from state import AgentState, WorkflowStep, NodeName
from llm_config import get_shared_llm
from technical_agent.tools import (
    build_technical_prompt,
    load_oem_catalog,
    extract_requirements,
    match_oem_products,
    build_comparison_table,
)


TECHNICAL_AGENT_PROMPT = """You are a Technical Analysis Agent for a B2B electrical cable manufacturing company.

**Your Role**:
Analyze selected RFPs and provide technical assessment.

**Analysis Areas**:
1. Technical Requirements - voltage ratings, cable types, specifications
2. Compliance Check - standards, certifications needed
3. Capacity Assessment - can we deliver the required quantity/timeline
4. Risk Factors - technical challenges, special requirements

**Output Format**:
- Use markdown formatting
- Be specific about technical details
- Highlight any concerns or advantages
- Recommend next steps
"""


def technical_agent_node(state: AgentState) -> Dict[str, Any]:
    """Analyzes the selected RFP technically."""
    print("\n" + "="*60)
    print("🔧 TECHNICAL AGENT STARTED")
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
        print("📋 Building technical prompt...")
        analysis_prompt = build_technical_prompt(selected_rfp)

        rfp_text = f"{selected_rfp.get('title', '')} {selected_rfp.get('description', '')}"
        requirements = extract_requirements(rfp_text)
        catalog = load_oem_catalog()
        recommendations = match_oem_products(catalog, requirements, top_n=3) if catalog else []
        comparison_table = build_comparison_table(recommendations) if recommendations else []

        matching_context = f"""
Extracted Requirements:
{json.dumps(requirements, indent=2, default=str)}

Top OEM Matches:
{json.dumps(recommendations, indent=2, default=str)}

Comparison Table:
{json.dumps(comparison_table, indent=2, default=str)}
"""

        messages = [
            SystemMessage(content=TECHNICAL_AGENT_PROMPT),
            HumanMessage(content=f"{analysis_prompt}\n\n{matching_context}")
        ]

        print("🤖 Calling LLM for technical analysis...")
        response = llm.invoke(messages)
        
        print(f"✅ Technical analysis complete. Response length: {len(response.content)} chars")
        print(f"🔄 Routing to: {NodeName.PRICING_AGENT}")
        print("="*60 + "\n")

        return {
            "messages": [AIMessage(content=response.content)],
            "technical_analysis": {
                "rfp_id": selected_rfp.get("rfp_id"),
                "analysis": response.content,
                "requirements": requirements,
                "recommended_products": recommendations,
                "comparison_table": comparison_table
            },
            "current_step": WorkflowStep.PRICING,
            "next_node": NodeName.PRICING_AGENT
        }

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"❌ Technical Agent Error:\n{error_details}")
        return {
            "messages": [AIMessage(content=f"❌ Error analyzing RFP: {str(e)}\n\nPlease check backend logs for details.")],
            "next_node": NodeName.END,
            "current_step": WorkflowStep.ERROR
        }
