#!/usr/bin/env python
"""
CLI entry point for HFO Crew Parallel orchestration.

Usage:
    python -m hfo_crew_parallel.cli [mission_context]
"""

import argparse
import sys
from pathlib import Path

from .config import CrewConfig, MissionIntent
from .swarmlord import SwarmlordOrchestrator


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="HFO Crew Parallel - Multi-crew parallel agent system"
    )
    parser.add_argument(
        'mission_context',
        nargs='?',
        default="Execute mission intent objectives with parallel lanes",
        help="Mission context and objectives"
    )
    parser.add_argument(
        '--mission-path',
        type=Path,
        help="Path to mission intent YAML file"
    )
    parser.add_argument(
        '--max-retries',
        type=int,
        default=3,
        help="Maximum retry attempts"
    )
    parser.add_argument(
        '--model',
        default='gpt-4o-mini',
        help="LLM model name"
    )
    
    args = parser.parse_args()
    
    config = CrewConfig(model_name=args.model)
    
    if not config.openai_api_key:
        print("ERROR: OPENAI_API_KEY not set in environment or .env file")
        print("\nTo use this system, you need to set up your API key:")
        print("1. Create a .env file in the repository root")
        print("2. Add: OPENAI_API_KEY=your_api_key_here")
        print("\nExample .env file:")
        print("OPENAI_API_KEY=sk-...")
        print("CREW_MODEL_NAME=gpt-4o-mini")
        print("EXPLORE_RATIO=0.6")
        print("EXPLOIT_RATIO=0.4")
        sys.exit(1)
    
    mission = MissionIntent(args.mission_path) if args.mission_path else MissionIntent()
    
    print(f"\n{'='*80}")
    print(f"HFO Crew Parallel Orchestrator")
    print(f"{'='*80}")
    print(f"Mission ID: {mission.mission_id}")
    print(f"Lanes: {mission.lanes_count} ({', '.join(mission.lane_names)})")
    print(f"Quorum: {mission.quorum_threshold} of {len(mission.quorum_validators)} validators")
    print(f"Model: {config.model_name}")
    print(f"Explore/Exploit: {config.explore_ratio:.0%}/{config.exploit_ratio:.0%}")
    print(f"{'='*80}\n")
    
    orchestrator = SwarmlordOrchestrator(config=config, mission_intent=mission)
    
    result = orchestrator.execute_mission(
        mission_context=args.mission_context,
        max_retries=args.max_retries
    )
    
    print(f"\n{'='*80}")
    print(f"Mission Result: {result['status'].upper()}")
    print(f"{'='*80}")
    print(f"\nAttempts: {result.get('attempt', result.get('attempts', 'N/A'))}")
    print(f"\nLane Results:")
    for lane_result in result.get('lane_results', []):
        print(f"  - {lane_result['lane']} ({lane_result['mode']}): {lane_result['status']}")
    
    print(f"\nVerification:")
    verify = result.get('verification', {})
    print(f"  Passed: {verify.get('passed', False)}")
    print(f"  Pass Count: {verify.get('pass_count', 'N/A')}")
    
    print(f"\n{'='*80}\n")
    
    return 0 if result['status'] == 'success' else 1


if __name__ == '__main__':
    sys.exit(main())
