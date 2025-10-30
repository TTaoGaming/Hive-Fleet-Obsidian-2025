#!/bin/bash
# Multi-Crew Orchestration Launcher
# Helps users run the system with proper checks

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=================================="
echo "HFO Multi-Crew Orchestration"
echo "=================================="
echo ""

# Check which mode
MODE="${1:-production}"

# Check if .env exists (only for production mode)
if [ "$MODE" = "production" ] || [ "$MODE" = "prod" ]; then
    if [ ! -f .env ]; then
        echo "⚠️  .env file not found"
        echo ""
        echo "To set up:"
        echo "  1. cp .env.example .env"
        echo "  2. Edit .env and add your OPENAI_API_KEY"
        echo ""
        echo "Or run the demo (no API key needed):"
        echo "  bash $0 demo"
        echo ""
        exit 1
    fi
fi

case "$MODE" in
    demo)
        echo "Running DEMO mission (no API calls)..."
        echo ""
        python scripts/demo_multi_crew_mission.py
        ;;
    test)
        echo "Running setup tests..."
        echo ""
        python scripts/test_multi_crew_setup.py
        ;;
    production|prod)
        echo "Running PRODUCTION mission (with LLM agents)..."
        echo ""
        
        # Check if API key is set
        if ! grep -q "OPENAI_API_KEY=sk-" .env 2>/dev/null; then
            echo "⚠️  OPENAI_API_KEY not configured in .env"
            echo ""
            echo "Edit .env and add your API key:"
            echo "  OPENAI_API_KEY=sk-your-key-here"
            echo ""
            echo "Or run the demo instead:"
            echo "  bash $0 demo"
            echo ""
            exit 1
        fi
        
        python scripts/hfo_multi_crew_orchestrator.py
        ;;
    *)
        echo "Usage: $0 [demo|test|production]"
        echo ""
        echo "Modes:"
        echo "  demo       - Run demonstration without API calls"
        echo "  test       - Run setup verification tests"
        echo "  production - Run full orchestration with LLM agents"
        echo ""
        exit 1
        ;;
esac

echo ""
echo "=================================="
echo "✓ Complete"
echo "=================================="
