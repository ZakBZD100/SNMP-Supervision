#!/bin/bash

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

# Stop all uvicorn processes (cleanup)
echo -e "${GREEN}Stopping all existing uvicorn processes...${NC}"
pkill -f uvicorn 2>/dev/null || true

# Free port 8000 (backend)
if lsof -i :8000 -t >/dev/null; then
  echo -e "${GREEN}Freeing port 8000 (backend)...${NC}"
  lsof -i :8000 -t | xargs -r kill -9
fi

# Free port 3000 (frontend)
if lsof -i :3000 -t >/dev/null; then
  echo -e "${GREEN}Freeing port 3000 (frontend)...${NC}"
  lsof -i :3000 -t | xargs -r kill -9
fi

# Open ports 3000 and 8000 in firewall (ufw)
if command -v sudo >/dev/null 2>&1 && command -v ufw >/dev/null 2>&1; then
  echo -e "${GREEN}Opening ports 3000 and 8000 in firewall (ufw)...${NC}"
  sudo ufw allow 3000 || true
  sudo ufw allow 8000 || true
fi

# Start backend with auto-restart if crash
source backend/venv/bin/activate
MAX_ATTEMPTS=3
ATTEMPT=1
BACKEND_OK=0
while [ $ATTEMPT -le $MAX_ATTEMPTS ]; do
  echo -e "${GREEN}Starting backend (attempt $ATTEMPT/${MAX_ATTEMPTS})...${NC}"
  nohup uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload > backend.log 2>&1 &
  BACKEND_PID=$!
  # Wait for backend to respond (max 20s)
  for i in {1..20}; do
    sleep 1
    if curl -s http://localhost:8000/docs >/dev/null; then
      BACKEND_OK=1
      break
    fi
    if ! kill -0 $BACKEND_PID 2>/dev/null; then
      echo -e "${RED}Backend crashed (PID $BACKEND_PID). Restarting...${NC}"
      break
    fi
  done
  if [ $BACKEND_OK -eq 1 ]; then
    echo -e "${GREEN}Backend started on http://localhost:8000 (PID $BACKEND_PID)${NC}"
    break
  fi
  kill $BACKEND_PID 2>/dev/null || true
  ATTEMPT=$((ATTEMPT+1))
  sleep 2
  echo -e "${RED}New backend startup attempt...${NC}"
done
if [ $BACKEND_OK -ne 1 ]; then
  echo -e "${RED}Failed to start backend after $MAX_ATTEMPTS attempts. Check backend.log.${NC}"
  exit 1
fi

# Show local IP to use
IP=$(hostname -I | awk '{print $1}')
echo -e "${GREEN}Access dashboard from another device : http://$IP:3000${NC}"
echo -e "${GREEN}Access API/docs : http://$IP:8000/docs${NC}"

# Start frontend on 0.0.0.0
cd frontend
echo -e "${GREEN}Frontend started on http://0.0.0.0:3000 (accessible on entire network)${NC}"
echo -e "${GREEN}To stop : Ctrl+C (backend will stop too)${NC}"

# Clean shutdown function
cleanup() {
  echo -e "\nStopping..."
  kill $BACKEND_PID 2>/dev/null || true
  exit 0
}
trap cleanup SIGINT

HOST=0.0.0.0 npm start
cleanup 