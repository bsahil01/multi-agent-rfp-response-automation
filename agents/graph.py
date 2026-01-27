from typing import Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from agents.state import AgentState, NodeName
from agents.main_agent.node import main_agent_node
from agents.sales_agent.node import sales_agent_node
from agents.technical_agent.node import technical_agent_node
from agents.pricing_agent.node import pricing_agent_node


def route_from_main(state: AgentState) -> str:
    next_node = state.get("next_node", NodeName.END)
    if next_node == NodeName.SALES_AGENT:
        return "sales_agent"
    elif next_node == NodeName.TECHNICAL_AGENT:
        return "technical_agent"
    return END


def route_from_sales(state: AgentState) -> str:
    return END


def route_from_technical(state: AgentState) -> str:
    next_node = state.get("next_node", NodeName.END)
    if next_node == NodeName.PRICING_AGENT:
        return "pricing_agent"
    return END


def route_from_pricing(state: AgentState) -> str:
    next_node = state.get("next_node", NodeName.END)
    if next_node == NodeName.MAIN_AGENT:
        return "main_agent"
    return END


def create_workflow() -> StateGraph:
    workflow = StateGraph(AgentState)

    workflow.add_node("main_agent", main_agent_node)
    workflow.add_node("sales_agent", sales_agent_node)
    workflow.add_node("technical_agent", technical_agent_node)
    workflow.add_node("pricing_agent", pricing_agent_node)

    workflow.set_entry_point("main_agent")

    workflow.add_conditional_edges(
        "main_agent",
        route_from_main,
        {
            "sales_agent": "sales_agent",
            "technical_agent": "technical_agent",
            END: END
        }
    )

    workflow.add_conditional_edges(
        "sales_agent",
        route_from_sales,
        {END: END}
    )

    workflow.add_conditional_edges(
        "technical_agent",
        route_from_technical,
        {
            "pricing_agent": "pricing_agent",
            END: END
        }
    )

    workflow.add_conditional_edges(
        "pricing_agent",
        route_from_pricing,
        {
            "main_agent": "main_agent",
            END: END
        }
    )

    memory = MemorySaver()
    app = workflow.compile(checkpointer=memory)

    return app


rfp_workflow = create_workflow()

__all__ = ["rfp_workflow"]
