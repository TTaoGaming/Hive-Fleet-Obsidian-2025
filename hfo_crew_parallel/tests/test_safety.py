"""
Tests for safety envelope.
"""

from pathlib import Path
import tempfile

from hfo_crew_parallel.safety import SafetyEnvelope


def test_check_line_count():
    """Test line count checking."""
    safety = SafetyEnvelope(chunk_size_max=10)
    
    content = "\n".join([f"line {i}" for i in range(5)])
    passed, count = safety.check_line_count(content)
    
    assert passed is True
    assert count == 5
    
    content_large = "\n".join([f"line {i}" for i in range(15)])
    passed, count = safety.check_line_count(content_large)
    
    assert passed is False
    assert count == 15


def test_check_placeholders():
    """Test placeholder detection."""
    safety = SafetyEnvelope()
    
    clean_content = "This is clean code\nwith no placeholders\n"
    passed, found = safety.check_placeholders(clean_content)
    
    assert passed is True
    assert len(found) == 0
    
    dirty_content = "This has TODO items\nand ... placeholders\nFIXME this\n"
    passed, found = safety.check_placeholders(dirty_content)
    
    assert passed is False
    assert len(found) > 0


def test_chunk_content():
    """Test content chunking."""
    safety = SafetyEnvelope(chunk_size_max=5)
    
    content = "\n".join([f"line {i}" for i in range(12)])
    chunks = safety.chunk_content(content)
    
    assert len(chunks) == 3
    
    for chunk in chunks[:-1]:
        assert len(chunk.split('\n')) == 5


def test_validate_file():
    """Test file validation."""
    safety = SafetyEnvelope(chunk_size_max=10)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.py"
        
        test_file.write_text("line 1\nline 2\nline 3\n")
        
        result = safety.validate_file(test_file)
        
        assert result['valid'] is True
        assert result['line_count'] == 3
        assert len(result['placeholders_found']) == 0
        
        test_file.write_text("TODO: implement this\nline 2\n")
        
        result = safety.validate_file(test_file)
        
        assert result['valid'] is False
        assert len(result['placeholders_found']) > 0
