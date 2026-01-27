import os
import json
from typing import Dict, Any
from datetime import datetime
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from state import AgentState, WorkflowStep, NodeName
from sales_agent.tools import scan_rfps_tool, qualify_rfp_tool, prioritize_rfps_tool
from llm_config import get_shared_llm

SALES_AGENT_SYSTEM_PROMPT = """You are an expert Sales Agent for a B2B electrical cable manufacturing company in India.


**Your Role**:
Help users find and evaluate RFP opportunities from tendersontime.com database.

**Available Tools**:
1. `scan_rfps_tool` - Search RFPs by keywords and date range
2. `qualify_rfp_tool` - Evaluate RFP against business criteria  
3. `prioritize_rfps_tool` - Rank RFPs by priority score

**Workflow**:
1. When user asks for RFPs, extract relevant keywords (products, specs, locations, project types)
2. Use `scan_rfps_tool` to search (typically 90 days ahead)
3. Qualify results using `qualify_rfp_tool` with smart criteria:
   - Min tender value: ₹10 lakhs - ₹50 crores (sweet spot)
   - Preferred locations: where we're competitive
   - Min days remaining: 7-21 days (realistic bid prep time)
4. Use `prioritize_rfps_tool` to get top 5 opportunities
5. Present results in clean markdown format with:
   - Brief context (scanned → qualified → top 5)
   - Clear listing of each RFP (title, organization, value, deadline, location)
   - Call-to-action: ask user to select RFP number for detailed analysis

**Output Format**:
- Use markdown formatting (headers, bold, lists)
- Be professional but conversational
- Keep it concise and actionable
- Include RFP numbers for easy reference

**Important**:
- Think through the criteria logically based on user's request
- Adjust qualification criteria if user specifies preferences
- If no RFPs found, suggest alternative search terms
"""


def sales_agent_node(state: AgentState) -> Dict[str, Any]:
    print("\n" + "="*60)
    print("📊 SALES AGENT STARTED")
    print("="*60)
    
    llm = get_shared_llm()

    try:
        keywords = ["cable", "wire", "electrical", "xlpe", "transmission", "power"]
        print(f"🔍 Scanning RFPs with keywords: {keywords}")
        scanned_rfps = scan_rfps_tool.invoke({"keywords": keywords, "days_ahead": 90})
        print(f"Found {len(scanned_rfps)} RFPs")

        if not scanned_rfps:
            return {
                "messages": [AIMessage(content="No RFPs found matching your criteria. Try different search terms.")],
                "next_node": NodeName.END,
                "current_step": WorkflowStep.COMPLETE
            }

        criteria = {
            "min_tender_value": 1000000,
            "min_days_remaining": 7,
            "preferred_locations": []
        }

        qualifications = []
        for rfp in scanned_rfps:
            qual = qualify_rfp_tool.invoke({"rfp": rfp, "criteria": criteria})
            qualifications.append(qual)

        top_rfps = prioritize_rfps_tool.invoke({
            "rfps": scanned_rfps,
            "qualifications": qualifications,
            "top_n": 5
        })

        if not top_rfps:
            return {
                "messages": [AIMessage(content="No RFPs qualified based on criteria. Try adjusting your requirements.")],
                "next_node": NodeName.END,
                "current_step": WorkflowStep.COMPLETE
            }

        rfp_data = json.dumps(top_rfps, indent=2, default=str)
        messages = [SystemMessage(content=SALES_AGENT_SYSTEM_PROMPT)] + list(state["messages"])

        format_prompt = f"""
Scanned: {len(scanned_rfps)} RFPs | Qualified: {len([q for q in qualifications if q.get('qualified')])} | Top: {len(top_rfps)}

Data:
```json
{rfp_data}
```

Present these RFPs professionally. Include RFP ID, title, organization, value, deadline, location, and score.
Ask user to select an RFP number for detailed technical analysis.
"""

        print("🤖 Calling LLM to format results...")
        response = llm.invoke(messages + [HumanMessage(content=format_prompt)])
        
        print(f"✅ Sales agent complete. Top {len(top_rfps)} RFPs identified")
        print(f"🔄 Routing to: {NodeName.END} (waiting for user selection)")
        print("="*60 + "\n")

        return {
            "messages": [AIMessage(content=response.content)],
            "rfps_identified": top_rfps,
            "current_step": WorkflowStep.WAITING_USER,
            "next_node": NodeName.END
        }

    except Exception as e:
        return {
            "messages": [AIMessage(content=f"Error: {str(e)}")],
            "next_node": NodeName.END,
            "current_step": WorkflowStep.ERROR
        }

