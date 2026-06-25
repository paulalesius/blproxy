#!/usr/bin/env python3
"""Test Python hook script for LLMPROXY_LOCK_SCRIPT."""

def handle_request(request_data):
    """Handle request hook."""
    phase = request_data.get("phase", "pre")
    
    print(f"[HOOK] Phase: {phase}")
    print(f"[HOOK] Method: {request_data.get('method')}")
    print(f"[HOOK] Path: {request_data.get('path')}")
    print(f"[HOOK] URL: {request_data.get('url')}")
    
    if phase == "post":
        print(f"[HOOK] Response status: {request_data.get('response_status')}")
    
    return {"handled": True}
