#!/bin/bash
# Test shell hook script for LLMPROXY_LOCK_SCRIPT

echo "[HOOK-SHELL] Phase: $LOCK_SCRIPT_PHASE"
echo "[HOOK-SHELL] Method: $LOCK_SCRIPT_METHOD"
echo "[HOOK-SHELL] Path: $LOCK_SCRIPT_PATH"
echo "[HOOK-SHELL] URL: $LOCK_SCRIPT_URL"

if [ "$LOCK_SCRIPT_PHASE" = "post" ]; then
    echo "[HOOK-SHELL] Response status: $LOCK_SCRIPT_RESPONSE_STATUS"
fi
