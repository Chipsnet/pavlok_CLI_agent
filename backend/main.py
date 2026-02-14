"""FastAPI Main Application for Oni System v0.3"""
import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from .api import (
    process_base_commit, process_stop, process_restart, process_config,
    process_plan_submit, process_remind_response, process_ignore_response,
)
from .api.signature import verify_slack_signature
from .api.internal_protection import verify_internal_request
from .models import Base


# ============================================================================
# Database Setup
# ============================================================================

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Get database URL from environment
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./oni.db"
)

# Create engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


# ============================================================================
# Lifespan Management
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    print(f"[{datetime.now()}] Starting Oni System v0.3 Backend...")
    print(f"[{datetime.now()}] Database URL: {DATABASE_URL}")

    # Create tables if not exists (for development)
    if "sqlite" in DATABASE_URL:
        Base.metadata.create_all(bind=engine)
        print(f"[{datetime.now()}] Database tables created/verified")

    yield

    # Shutdown
    print(f"[{datetime.now()}] Shutting down Oni System v0.3 Backend...")


# ============================================================================
# FastAPI App
# ============================================================================

app = FastAPI(
    title="Oni System v0.3",
    description="Pavlok-based commitment system with Slack integration",
    version="0.3.0",
    lifespan=lifespan,
)


# ============================================================================
# Middleware
# ============================================================================

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests."""
    start_time = datetime.now()
    response = await call_next(request)
    duration = (datetime.now() - start_time).total_seconds()
    print(f"[{datetime.now()}] {request.method} {request.url.path} - {response.status_code} ({duration:.3f}s)")
    return response


# ============================================================================
# Health Check
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "version": "0.3.0",
        "timestamp": datetime.now().isoformat()
    }


# ============================================================================
# Slack Webhook Endpoints
# ============================================================================

@app.post("/slack/command")
async def slack_command(request: Request):
    """Handle Slack slash commands."""
    # Verify signature
    if not await verify_slack_signature(request):
        return JSONResponse(
            status_code=401,
            content={"error": "Invalid signature"}
        )

    # Parse command
    form_data = await request.form()
    command = form_data.get("command")
    user_id = form_data.get("user_id")

    print(f"[{datetime.now()}] Slack command: {command} from user {user_id}")

    # Route to appropriate handler
    if command == "/base_commit":
        return await process_base_commit(form_data)
    elif command == "/stop":
        return await process_stop(form_data)
    elif command == "/restart":
        return await process_restart(form_data)
    elif command == "/config":
        return await process_config(form_data)
    else:
        return JSONResponse(
            status_code=400,
            content={"error": f"Unknown command: {command}"}
        )


@app.post("/slack/interactive")
async def slack_interactive(request: Request):
    """Handle Slack interactive components (buttons, modals)."""
    # Verify signature
    if not await verify_slack_signature(request):
        return JSONResponse(
            status_code=401,
            content={"error": "Invalid signature"}
        )

    # Parse payload
    form_data = await request.form()
    payload = form_data.get("payload")

    if not payload:
        return JSONResponse(
            status_code=400,
            content={"error": "Missing payload"}
        )

    import json
    payload_data = json.loads(payload)

    action_type = payload_data.get("type")
    user_id = payload_data.get("user", {}).get("id")

    print(f"[{datetime.now()}] Slack interactive: {action_type} from user {user_id}")

    # Route to appropriate handler
    if action_type == "view_submission":
        # Modal submission
        callback_id = payload_data.get("view", {}).get("callback_id")
        if callback_id == "commitment_submit":
            return await process_plan_submit(payload_data)
        elif callback_id == "config_submit":
            return await process_config(payload_data)
    elif action_type == "block_actions":
        # Button click
        actions = payload_data.get("actions", [])
        if actions:
            action_id = actions[0].get("action_id")
            if action_id == "remind_yes":
                return await process_remind_response(payload_data, "YES")
            elif action_id == "remind_no":
                return await process_remind_response(payload_data, "NO")
            elif action_id == "ignore_respond":
                return await process_ignore_response(payload_data)

    return JSONResponse(
        status_code=400,
        content={"error": f"Unknown action type: {action_type}"}
    )


# ============================================================================
# Internal Endpoints (for Worker)
# ============================================================================

@app.post("/internal/execute/{event_type}")
async def internal_execute(event_type: str, request: Request):
    """Handle internal execution requests from Worker."""
    # Verify internal request
    if not await verify_internal_request(request):
        return JSONResponse(
            status_code=401,
            content={"error": "Unauthorized"}
        )

    print(f"[{datetime.now()}] Internal execute: {event_type}")

    # TODO: Implement event execution logic
    return {
        "status": "ok",
        "event_type": event_type
    }


@app.get("/internal/execute/{event_type}")
async def internal_execute_get(event_type: str, request: Request):
    """Handle internal execution requests from Worker (GET for testing)."""
    # Verify internal request
    if not await verify_internal_request(request):
        return JSONResponse(
            status_code=401,
            content={"error": "Unauthorized"}
        )

    print(f"[{datetime.now()}] Internal execute (GET): {event_type}")

    # TODO: Implement event execution logic
    return {
        "status": "ok",
        "event_type": event_type
    }


@app.get("/internal/config/{key}")
async def internal_get_config(key: str, request: Request):
    """Get configuration value for Worker."""
    # Verify internal request
    if not await verify_internal_request(request):
        return JSONResponse(
            status_code=401,
            content={"error": "Unauthorized"}
        )

    print(f"[{datetime.now()}] Internal config: {key}")

    # TODO: Implement config retrieval
    return {
        "key": key,
        "value": None  # TODO: Get from database
    }


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    import traceback
    print(f"[{datetime.now()}] ERROR: {exc}")
    print(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )


# ============================================================================
# Development Server
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
