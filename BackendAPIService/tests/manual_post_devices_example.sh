#!/usr/bin/env bash
# Simple manual test for POST /devices endpoint. Requires server running on localhost:3001
set -euo pipefail

API_BASE="${API_BASE:-http://localhost:3001}"
echo "Posting sample device to $API_BASE/devices"
curl -s -i -H "Content-Type: application/json" -X POST "$API_BASE/devices" \
  --data '{
    "name": "Test Router",
    "ip_address": "192.168.1.10",
    "type": "router",
    "location": "Lab A",
    "status": "unknown"
  }' | sed -e 's/\r$//'
echo
echo "Posting duplicate to verify 409 handling"
curl -s -i -H "Content-Type: application/json" -X POST "$API_BASE/devices" \
  --data '{
    "name": "Test Router 2",
    "ip_address": "192.168.1.10",
    "type": "router",
    "location": "Lab B",
    "status": "offline"
  }' | sed -e 's/\r$//'
echo
