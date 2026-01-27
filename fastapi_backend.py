
"""
FastAPI Backend for RFP Automation System
Provides REST APIs for:
- OEM Catalog Management
- Chat Interface
- RFP Workflow Management
- Dashboard Data
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json
from datetime import datetime
import os

from models import AnalyzeRFPRequest, ChatMessage, ChatResponse, OEMProduct, RFPScanRequest
from utils import save_catalog, save_test_pricing

# Initialize FastAPI app
app = FastAPI(
    title="RFP Automation System",
    description="AI-powered B2B RFP Response Automation",
    version="1.0.0"
)

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# IN-MEMORY STORAGE (Replace with database in production)
# ============================================================

# Storage
oem_catalog_db = []
chat_sessions = {}
test_pricing_db = {}

# LangGraph manages sessions internally with MemorySaver

# ============================================================
# STARTUP EVENT
# ============================================================

@app.on_event("startup")
async def startup_event():
    """Load initial data on startup"""
    global oem_catalog_db, test_pricing_db

    if os.path.exists('data/catalog.json'):
        with open('data/catalog.json', 'r') as f:
            oem_catalog_db = json.load(f)

    if os.path.exists('data/test_pricing.json'):
        with open('data/test_pricing.json', 'r') as f:
            test_pricing_db = json.load(f)

    print("✅ RFP Automation System initialized (LangGraph)")

# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/")
async def root():
    return {
        "status": "online",
        "service": "RFP Automation System",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "agents": "LangGraph workflow active",
        "catalog_items": len(oem_catalog_db),
        "test_types": len(test_pricing_db)
    }


@app.get("/api/reports/{session_id}/{rfp_id}")
async def get_report(session_id: str, rfp_id: str):
    """Download generated RFP report PDF."""
    safe_rfp_id = rfp_id.replace("/", "_")
    report_path = os.path.join("data", "reports", f"{session_id}_{safe_rfp_id}.pdf")
    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(report_path, media_type="application/pdf", filename=os.path.basename(report_path))

# ============================================================
# OEM CATALOG MANAGEMENT APIs
# ============================================================

@app.get("/api/catalog", response_model=List[OEMProduct])
async def get_catalog():
    """Get all OEM products from catalog"""
    return oem_catalog_db

@app.post("/api/catalog", response_model=OEMProduct)
async def add_product(product: OEMProduct):
    """Add new product to catalog"""
    # Check if SKU already exists
    if any(p['sku'] == product.sku for p in oem_catalog_db):
        raise HTTPException(status_code=400, detail="SKU already exists")

    product_dict = product.dict()
    product_dict['created_at'] = datetime.now().isoformat()
    product_dict['updated_at'] = datetime.now().isoformat()

    oem_catalog_db.append(product_dict)

    save_catalog(oem_catalog_db)

    return product_dict

@app.put("/api/catalog/{sku}", response_model=OEMProduct)
async def update_product(sku: str, product: OEMProduct):
    """Update existing product"""
    for i, p in enumerate(oem_catalog_db):
        if p['sku'] == sku:
            product_dict = product.dict()
            product_dict['updated_at'] = datetime.now().isoformat()
            product_dict['created_at'] = p.get('created_at', datetime.now().isoformat())
            oem_catalog_db[i] = product_dict

            save_catalog(oem_catalog_db)
            return product_dict

    raise HTTPException(status_code=404, detail="Product not found")

@app.delete("/api/catalog/{sku}")
async def delete_product(sku: str):
    """Delete product from catalog"""
    for i, p in enumerate(oem_catalog_db):
        if p['sku'] == sku:
            oem_catalog_db.pop(i)

            save_catalog(oem_catalog_db)
            return {"message": "Product deleted successfully"}

    raise HTTPException(status_code=404, detail="Product not found")

@app.post("/api/catalog/upload")
async def upload_catalog(file: UploadFile = File(...)):
    """Upload catalog from Excel/CSV file"""
    try:
        contents = await file.read()

        # Parse based on file type
        if file.filename.endswith('.json'):
            new_products = json.loads(contents)
        elif file.filename.endswith('.csv'):
            # Parse CSV (implement CSV parsing)
            raise HTTPException(status_code=400, detail="CSV parsing not implemented yet")
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format")

        # Add to catalog
        for product in new_products:
            if not any(p['sku'] == product['sku'] for p in oem_catalog_db):
                product['created_at'] = datetime.now().isoformat()
                product['updated_at'] = datetime.now().isoformat()
                oem_catalog_db.append(product)

        save_catalog(oem_catalog_db)

        return {
            "message": f"Successfully uploaded {len(new_products)} products",
            "total_products": len(oem_catalog_db)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ============================================================
# CHAT APIs
# ============================================================

@app.post("/api/chat", response_model=ChatResponse)
async def chat(message: ChatMessage):
    from agents.graph import rfp_workflow
    from agents.state import create_initial_state, get_last_ai_message_content
    from langchain_core.messages import HumanMessage

    session_id = message.session_id

    try:
        prior_state = chat_sessions.get(session_id)
        if prior_state:
            state = dict(prior_state)
            state["messages"] = list(prior_state.get("messages", [])) + [HumanMessage(content=message.message)]
        else:
            state = create_initial_state(session_id, message.message)

        result = await rfp_workflow.ainvoke(
            state,
            config={"configurable": {"thread_id": session_id}}
        )

        response_text = get_last_ai_message_content(result)
        chat_sessions[session_id] = result

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
        return ChatResponse(
            response=f"Error: {str(e)}",
            session_id=session_id,
            timestamp=datetime.now().isoformat(),
            workflow_state={"status": "ERROR", "error": str(e)}
        )

@app.get("/api/chat/history/{session_id}")
async def get_chat_history(session_id: str):
    """Get chat history for a session (LangGraph manages this internally)"""
    return {"message": "Chat history is managed by LangGraph checkpointer"}

@app.get("/api/chat/state/{session_id}")
async def get_workflow_state(session_id: str):
    """Get current workflow state (managed by LangGraph)"""
    return {"message": "Workflow state managed by LangGraph checkpointer", "session_id": session_id}

@app.delete("/api/chat/{session_id}")
async def clear_session(session_id: str):
    """Clear chat session"""
    return {"message": "Session cleared (LangGraph handles cleanup)", "session_id": session_id}

# ============================================================
# RFP WORKFLOW APIs
# ============================================================

@app.post("/api/rfp/scan")
async def scan_rfps(request: RFPScanRequest):
    """Scan for RFPs (use /api/chat for LangGraph workflow)"""
    return {
        "message": "Please use /api/chat endpoint for RFP workflow with LangGraph agents",
        "total_found": 0,
        "rfps": []
    }

@app.post("/api/rfp/analyze")
async def analyze_rfp(request: AnalyzeRFPRequest):
    """Analyze a specific RFP"""
    # This would typically fetch from database
    # For now, return mock analysis
    return {
        "rfp_id": request.rfp_id,
        "status": "analyzed",
        "message": "Use chat interface for full workflow"
    }

@app.get("/api/dashboard/stats")
async def get_dashboard_stats():
    """Get dashboard statistics"""
    return {
        "total_products": len(oem_catalog_db),
        "test_types": len(test_pricing_db),
        "system_status": "operational",
        "last_updated": datetime.now().isoformat()
    }