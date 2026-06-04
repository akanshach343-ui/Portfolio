#!/bin/bash
# Start the portfolio backend server
# Run: bash start.sh

echo "═══════════════════════════════════════════"
echo "  Akansha's Portfolio — RayCreates Proposal"
echo "═══════════════════════════════════════════"
echo ""
echo "  Installing dependencies..."
pip install -r requirements.txt -q

echo ""
echo "  Starting server on http://localhost:8000"
echo ""
echo "  → Visit:  http://localhost:8000"
echo "  → API:    http://localhost:8000/api/health"
echo "  → Docs:   http://localhost:8000/docs"
echo "  → Challenges: http://localhost:8000/api/challenges"
echo ""
echo "  Press Ctrl+C to stop."
echo "═══════════════════════════════════════════"

python -m uvicorn main:app --reload --port 8000