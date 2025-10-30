"""
Tests for configuration management.
"""

import tempfile
from pathlib import Path
import yaml

from hfo_crew_parallel.config import MissionIntent, CrewConfig


def test_mission_intent_load():
    """Test loading mission intent from YAML."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mission_file = Path(tmpdir) / "mission.yml"
        
        mission_data = {
            'mission_id': 'test_mission',
            'lanes': {
                'count': 3,
                'names': ['lane_a', 'lane_b', 'lane_c']
            },
            'quorum': {
                'threshold': 2,
                'validators': ['immunizer', 'disruptor']
            },
            'safety': {
                'chunk_size_max': 150,
                'placeholder_ban': True
            }
        }
        
        with open(mission_file, 'w') as f:
            yaml.dump(mission_data, f)
        
        mission = MissionIntent(mission_file)
        
        assert mission.mission_id == 'test_mission'
        assert mission.lanes_count == 3
        assert mission.lane_names == ['lane_a', 'lane_b', 'lane_c']
        assert mission.quorum_threshold == 2
        assert mission.chunk_size_max == 150
        assert mission.placeholder_ban is True


def test_mission_intent_defaults():
    """Test mission intent defaults when file doesn't exist."""
    mission = MissionIntent(Path("/nonexistent/mission.yml"))
    
    assert mission.lanes_count == 2
    assert mission.quorum_threshold == 2
    assert mission.chunk_size_max == 200


def test_crew_config_defaults():
    """Test crew config defaults."""
    config = CrewConfig()
    
    assert config.model_name == 'gpt-4o-mini'
    assert config.temperature == 0.1
    assert config.explore_ratio == 0.6
    assert config.exploit_ratio == 0.4
