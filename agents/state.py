from typing import TypedDict, List, Dict, Optional, Any, Annotated
from langchain_core.messages import BaseMessage
import operator


class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    current_step: str
    next_node: str
    rfps_identified: List[Dict[str, Any]]
    selected_rfp: Optional[Dict[str, Any]]
    user_selected_rfp_id: Optional[str]
    technical_analysis: Optional[Dict[str, Any]]
    pricing_analysis: Optional[Dict[str, Any]]
    final_response: Optional[str]
    report_path: Optional[str]
    report_url: Optional[str]
    product_summary: Optional[str]
    test_summary: Optional[str]
    waiting_for_user: bool
    user_prompt: Optional[str]
    agent_reasoning: List[Dict[str, Any]]
    tool_calls_made: List[Dict[str, Any]]
    session_id: str
    error: Optional[str]


# Workflow step constants for type safety
class WorkflowStep:
    IDLE = "IDLE"
    SCANNING = "SCANNING"
    WAITING_USER = "WAITING_USER"
    ANALYZING = "ANALYZING"
    PRICING = "PRICING"
    COMPLETE = "COMPLETE"
    ERROR = "ERROR"


class NodeName:
    MAIN_AGENT = "main_agent"
    SALES_AGENT = "sales_agent"
    TECHNICAL_AGENT = "technical_agent"
    PRICING_AGENT = "pricing_agent"
    WAIT_FOR_USER = "wait_for_user"
    END = "END"


def create_initial_state(session_id: str, user_message: str) -> AgentState:
    from langchain_core.messages import HumanMessage
    
    return {
        "messages": [HumanMessage(content=user_message)],
        "current_step": WorkflowStep.IDLE,
        "next_node": NodeName.MAIN_AGENT,
        "rfps_identified": [],
        "selected_rfp": None,
        "user_selected_rfp_id": None,
        "technical_analysis": None,
        "pricing_analysis": None,
        "final_response": None,
        "report_path": None,
        "report_url": None,
        "product_summary": None,
        "test_summary": None,
        "waiting_for_user": False,
        "user_prompt": None,
        "agent_reasoning": [],
        "tool_calls_made": [],
        "session_id": session_id,
        "error": None
    }


def is_waiting_for_user(state: AgentState) -> bool:
    return state.get("waiting_for_user", False)


def has_error(state: AgentState) -> bool:
    return state.get("error") is not None


def is_complete(state: AgentState) -> bool:
    return state.get("current_step") == WorkflowStep.COMPLETE


def get_last_ai_message_content(state: AgentState) -> str:
    from langchain_core.messages import AIMessage
    
    for message in reversed(state["messages"]):
        if isinstance(message, AIMessage):
            return message.content
    return "Processing your request..."
