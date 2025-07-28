#!/bin/bash

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}Stopping SNMP Supervision...${NC}"

# Stop backend processes
echo -e "${GREEN}Stopping backend processes...${NC}"
pkill -f uvicorn 2>/dev/null || true
pkill -f "python.*main.py" 2>/dev/null || true

# Stop frontend processes
echo -e "${GREEN}Stopping frontend processes...${NC}"
pkill -f "npm start" 2>/dev/null || true
pkill -f "react-scripts" 2>/dev/null || true

# Free ports
echo -e "${GREEN}Freeing ports...${NC}"
if lsof -i :8000 -t >/dev/null; then
  lsof -i :8000 -t | xargs -r kill -9
fi

if lsof -i :3000 -t >/dev/null; then
  lsof -i :3000 -t | xargs -r kill -9
fi

echo -e "${GREEN}SNMP Supervision stopped successfully!${NC}" 