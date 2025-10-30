"""
Configuration management for crew operations.

Loads mission intent and manages environment configuration.
"""

import os
import yaml
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class CrewConfig:
    """Environment configuration for crew operations."""
    
    def __init__(self, **kwargs):
        """Initialize configuration from environment or kwargs."""
        self.openai_api_key = kwargs.get('openai_api_key') or os.getenv('OPENAI_API_KEY')
        self.anthropic_api_key = kwargs.get('anthropic_api_key') or os.getenv('ANTHROPIC_API_KEY')
        self.langchain_api_key = kwargs.get('langchain_api_key') or os.getenv('LANGCHAIN_API_KEY')
        
        self.model_name = kwargs.get('model_name') or os.getenv('CREW_MODEL_NAME', 'gpt-4o-mini')
        self.temperature = float(kwargs.get('temperature') or os.getenv('CREW_TEMPERATURE', '0.1'))
        self.max_iter = int(kwargs.get('max_iter') or os.getenv('CREW_MAX_ITER', '5'))
        
        self.blackboard_path = kwargs.get('blackboard_path') or os.getenv(
            'BLACKBOARD_PATH', 
            'hfo_blackboard/obsidian_synapse_blackboard.jsonl'
        )
        
        self.explore_ratio = float(kwargs.get('explore_ratio') or os.getenv('EXPLORE_RATIO', '0.6'))
        self.exploit_ratio = float(kwargs.get('exploit_ratio') or os.getenv('EXPLOIT_RATIO', '0.4'))


class MissionIntent:
    """Loads and manages mission intent YAML."""
    
    def __init__(self, mission_path: Optional[Path] = None):
        """Initialize mission intent loader.
        
        Args:
            mission_path: Path to mission YAML file. If None, loads today's mission.
        """
        if mission_path is None:
            today = datetime.now().strftime("%Y-%m-%d")
            mission_path = Path(f"hfo_mission_intent/{today}/mission_intent_daily_{today}.v5.yml")
        
        self.mission_path = Path(mission_path)
        self.data: Dict[str, Any] = {}
        
        if self.mission_path.exists():
            self.load()
    
    def load(self) -> None:
        """Load mission intent from YAML file."""
        with open(self.mission_path, 'r') as f:
            self.data = yaml.safe_load(f)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get mission intent value by key.
        
        Args:
            key: Key to retrieve (supports dot notation)
            default: Default value if key not found
            
        Returns:
            Value or default
        """
        keys = key.split('.')
        value = self.data
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        
        return value
    
    @property
    def mission_id(self) -> str:
        """Get mission ID."""
        return self.data.get('mission_id', 'unknown')
    
    @property
    def lanes_count(self) -> int:
        """Get number of parallel lanes."""
        return self.data.get('lanes', {}).get('count', 2)
    
    @property
    def lane_names(self) -> list:
        """Get lane names."""
        return self.data.get('lanes', {}).get('names', ['lane_a', 'lane_b'])
    
    @property
    def quorum_threshold(self) -> int:
        """Get verification quorum threshold."""
        return self.data.get('quorum', {}).get('threshold', 2)
    
    @property
    def quorum_validators(self) -> list:
        """Get quorum validator names."""
        return self.data.get('quorum', {}).get('validators', 
            ['immunizer', 'disruptor', 'verifier_aux'])
    
    @property
    def chunk_size_max(self) -> int:
        """Get maximum chunk size."""
        return self.data.get('safety', {}).get('chunk_size_max', 200)
    
    @property
    def placeholder_ban(self) -> bool:
        """Check if placeholders are banned."""
        return self.data.get('safety', {}).get('placeholder_ban', True)
