"""
Safety envelope enforcement for crew operations.

Implements chunk limits, tripwires, and revert mechanisms
as specified in AGENTS.md.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class SafetyEnvelope:
    """Enforces safety constraints on agent operations."""
    
    CHUNK_SIZE_MAX = 200
    PLACEHOLDER_PATTERNS = [
        r'\bTODO\b',
        r'\.\.\.(?!\w)',  # ellipsis not part of a word
        r'\bomitted\b',
        r'\bFIXME\b',
        r'\bXXX\b',
    ]
    
    def __init__(self, chunk_size_max: int = CHUNK_SIZE_MAX):
        """Initialize safety envelope.
        
        Args:
            chunk_size_max: Maximum lines per chunk write
        """
        self.chunk_size_max = chunk_size_max
        self.tripwires: Dict[str, bool] = {}
    
    def check_line_count(self, content: str, min_target: Optional[int] = None) -> Tuple[bool, int]:
        """Check if line count meets requirements.
        
        Args:
            content: Content to check
            min_target: Minimum target line count (optional)
            
        Returns:
            (passed, line_count)
        """
        line_count = len(content.strip().split('\n'))
        
        if min_target is not None:
            passed = line_count >= int(min_target * 0.9)  # 90% of target
        else:
            passed = line_count <= self.chunk_size_max
        
        self.tripwires['line_count'] = passed
        return passed, line_count
    
    def check_placeholders(self, content: str) -> Tuple[bool, List[str]]:
        """Check for placeholder patterns.
        
        Args:
            content: Content to check
            
        Returns:
            (passed, list of found placeholders)
        """
        found_placeholders = []
        
        for pattern in self.PLACEHOLDER_PATTERNS:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                found_placeholders.append(match.group())
        
        passed = len(found_placeholders) == 0
        self.tripwires['placeholder_scan'] = passed
        return passed, found_placeholders
    
    def chunk_content(self, content: str, max_lines: Optional[int] = None) -> List[str]:
        """Split content into chunks respecting line limits.
        
        Args:
            content: Content to chunk
            max_lines: Maximum lines per chunk (defaults to chunk_size_max)
            
        Returns:
            List of content chunks
        """
        max_lines = max_lines or self.chunk_size_max
        lines = content.split('\n')
        chunks = []
        
        current_chunk = []
        for line in lines:
            current_chunk.append(line)
            
            if len(current_chunk) >= max_lines:
                chunks.append('\n'.join(current_chunk))
                current_chunk = []
        
        if current_chunk:
            chunks.append('\n'.join(current_chunk))
        
        return chunks
    
    def validate_file(self, file_path: Path) -> Dict[str, any]:
        """Validate a file against safety constraints.
        
        Args:
            file_path: Path to file to validate
            
        Returns:
            Validation result dict
        """
        if not file_path.exists():
            return {
                'valid': False,
                'error': 'File does not exist'
            }
        
        content = file_path.read_text()
        
        line_check_passed, line_count = self.check_line_count(content)
        placeholder_check_passed, placeholders = self.check_placeholders(content)
        
        return {
            'valid': line_check_passed and placeholder_check_passed,
            'line_count': line_count,
            'chunk_size_max': self.chunk_size_max,
            'placeholders_found': placeholders,
            'tripwires': dict(self.tripwires)
        }
    
    def get_status(self) -> Dict[str, any]:
        """Get current safety envelope status.
        
        Returns:
            Status dictionary
        """
        return {
            'chunk_size_max': self.chunk_size_max,
            'tripwires': dict(self.tripwires),
            'all_clear': all(self.tripwires.values())
        }
