from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from ..models import ChatMessage, ChatResponse
from ..core.config import chat_sessions
from ..core.config import REPORTS_DIR
from ..core.memory_manager import memory_manager
from ..core.db.client import drizzle_client
from datetime import datetime
from fastapi.responses import FileResponse

router = APIRouter(prefix="/api/chat", tags=["chat"])

@router.post("", response_model=ChatResponse)
async def chat(message: ChatMessage):
    from agents.graph import rfp_workflow
    from agents.state import create_initial_state, get_last_ai_message_content
    from langchain_core.messages import HumanMessage

    session_id = message.session_id

    try:
        # Try to load existing state from Supabase first
        state = await memory_manager.load_agent_state(session_id)
        
        if state:
            # Load existing state
            state["messages"] = [HumanMessage(content=message.message)]
        else:
            # Create new state
            state = create_initial_state(session_id, message.message)
        
        # Add user message to memory
        await memory_manager.add_user_message(session_id, message.message)
        
        # Log agent interaction start
        await memory_manager.log_agent_interaction(
            session_id=session_id,
            agent_name="main_agent",
            input_data={"message": message.message},
            output_data={},
            reasoning="Starting RFP workflow"
        )
        
        # Run the workflow
        result = await rfp_workflow.ainvoke(
            state,
            config={"configurable": {"thread_id": session_id}}
        )
        
        # Get response
        response_text = get_last_ai_message_content(result)
        
        # Add AI response to memory
        await memory_manager.add_ai_message(
            session_id=session_id,
            message=response_text,
            metadata={
                "current_step": result.get("current_step"),
                "rfps_identified": result.get("rfps_identified", [])
            }
        )
        
        # Save complete state
        await memory_manager.save_agent_state(session_id, result)
        
        # Update in-memory sessions for compatibility
        chat_sessions[session_id] = result
        
        # Log completion
        await memory_manager.log_agent_interaction(
            session_id=session_id,
            agent_name="main_agent",
            input_data={"message": message.message},
            output_data={"response": response_text, "state": result.get("current_step")},
            reasoning=f"Completed workflow step: {result.get('current_step')}"
        )
        
        return ChatResponse(
            response=response_text,
            session_id=session_id,
            timestamp=datetime.now().isoformat(),
            workflow_state={
                "current_step": result.get("current_step", "COMPLETE"),
                "rfps_identified": result.get("rfps_identified", []),
                "report_url": result.get("report_url")
            }
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        
        # Log error
        await memory_manager.log_agent_interaction(
            session_id=session_id,
            agent_name="main_agent",
            input_data={"message": message.message},
            output_data={},
            reasoning=f"Error occurred: {str(e)}"
        )
        
        return ChatResponse(
            response=f"Error: {str(e)}",
            session_id=session_id,
            timestamp=datetime.now().isoformat(),
            workflow_state={"current_step": "ERROR"}
        )


@router.get("/history/{session_id}")
async def get_chat_history(session_id: str, limit: int = 50):
    """Get chat history for a session"""
    try:
        messages = await drizzle_client.get_chat_messages(session_id, limit)
        
        return {
            "session_id": session_id,
            "messages": messages,
            "total": len(messages)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching chat history: {str(e)}")


@router.get("/sessions/{user_id}")
async def get_user_sessions(user_id: str):
    """Get all sessions for a user (if user_id is implemented)"""
    try:
        # For now, return session stats from memory manager
        # In future, this would query Supabase for user's sessions
        return {
            "user_id": user_id,
            "sessions": [],  # Implement user session tracking
            "message": "User session tracking not yet implemented"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching sessions: {str(e)}")


@router.delete("/sessions/{session_id}")
async def clear_session(session_id: str):
    """Clear a chat session"""
    try:
        # Clear from memory
        memory_manager.clear_memory(session_id)
        
        # Remove from in-memory sessions
        if session_id in chat_sessions:
            del chat_sessions[session_id]
        
        return {"message": f"Session {session_id} cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing session: {str(e)}")


@router.get("/stats/{session_id}")
async def get_session_stats(session_id: str):
    """Get statistics for a session"""
    try:
        stats = memory_manager.get_session_stats(session_id)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting session stats: {str(e)}")


@router.get("/state/{session_id}")
async def get_workflow_state(session_id: str):
    """Get current workflow state (managed by LangGraph)"""
    state = chat_sessions.get(session_id)
    if not state:
        return {"session_id": session_id, "exists": False}

    def get_rfp_id(rfp: Dict[str, Any]) -> str:
        return rfp.get("id") or rfp.get("rfp_id", "")

    rfps_identified = state.get("rfps_identified", []) or []
    selected_rfp = state.get("selected_rfp")

    rfps_summary = [
        {
            "id": get_rfp_id(r),
            "title": r.get("title"),
            "client": r.get("client"),
            "estimated_value": r.get("estimated_value") or r.get("value"),
            "submission_deadline": r.get("submission_deadline"),
            "priority_score": r.get("priority_score"),
        }
        for r in rfps_identified
        if isinstance(r, dict)
    ]

    selected_rfp_summary = None
    if isinstance(selected_rfp, dict):
        selected_rfp_summary = {
            "id": get_rfp_id(selected_rfp),
            "title": selected_rfp.get("title"),
            "client": selected_rfp.get("client"),
        }

    return {
        "session_id": session_id,
        "exists": True,
        "current_step": state.get("current_step"),
        "next_node": state.get("next_node"),
        "waiting_for_user": state.get("waiting_for_user", False),
        "rfps_identified": rfps_summary,
        "selected_rfp": selected_rfp_summary,
        "report_url": state.get("report_url"),
        "error": state.get("error"),
    }

@router.delete("/{session_id}")
async def clear_session(session_id: str):
    """Clear chat session"""
    chat_sessions.pop(session_id, None)
    return {"message": "Session cleared", "session_id": session_id}
