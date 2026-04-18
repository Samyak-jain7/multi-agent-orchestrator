#!/bin/bash
# Smoke test for backend
# Starts the server with in-memory DB, hits health/ready,
# creates an agent, lists agents, and asserts the created agent appears in the list.
# Exit 0 on success, 1 on failure.

set -e

BACKEND_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$BACKEND_DIR"

# Use in-memory DB
export DATABASE_URL="sqlite+aiosqlite:///:memory:"
export OPENAI_API_KEY="test-key"
export MINIMAX_API_KEY="test-key"
export APP_API_KEY=""
export LOG_LEVEL="WARNING"

PORT=18080
BASE_URL="http://localhost:$PORT"

# Start server in background
uvicorn main:app --host 127.0.0.1 --port $PORT &
SERVER_PID=$!

cleanup() {
  echo "Stopping server (PID $SERVER_PID)..."
  kill $SERVER_PID 2>/dev/null || true
  wait $SERVER_PID 2>/dev/null || true
}
trap cleanup EXIT

# Wait for server to start
echo "Waiting for server to start..."
for i in $(seq 1 30); do
  if curl -s "$BASE_URL/health" > /dev/null 2>&1; then
    echo "Server is up!"
    break
  fi
  if [ $i -eq 30 ]; then
    echo "ERROR: Server failed to start within 30 seconds"
    exit 1
  fi
  sleep 1
done

# ---- /health ----
echo "Testing /health..."
HEALTH=$(curl -s "$BASE_URL/health")
echo "Health response: $HEALTH"
if ! echo "$HEALTH" | grep -q '"status"'; then
  echo "ERROR: /health missing status field"
  exit 1
fi

# ---- /ready ----
echo "Testing /ready..."
READY=$(curl -s "$BASE_URL/ready")
echo "Ready response: $READY"
if ! echo "$READY" | grep -q '"ready"'; then
  echo "ERROR: /ready missing ready field"
  exit 1
fi

# ---- Create agent ----
echo "Creating agent..."
CREATE_RESP=$(curl -s -X POST "$BASE_URL/api/v1/agents" \
  -H "Content-Type: application/json" \
  -d '{"name":"Smoke Test Agent","description":"Created by smoke test","model_provider":"minimax","model_name":"MiniMax-M2.7","system_prompt":"You are a smoke test agent."}')
echo "Create response: $CREATE_RESP"

AGENT_ID=$(echo "$CREATE_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo "")
if [ -z "$AGENT_ID" ]; then
  echo "ERROR: Agent creation returned no ID"
  exit 1
fi
echo "Created agent ID: $AGENT_ID"

# ---- List agents ----
echo "Listing agents..."
LIST_RESP=$(curl -s "$BASE_URL/api/v1/agents")
echo "List response: $LIST_RESP"

if ! echo "$LIST_RESP" | grep -q "$AGENT_ID"; then
  echo "ERROR: Created agent $AGENT_ID not found in agent list"
  exit 1
fi

echo "All smoke tests passed!"
exit 0