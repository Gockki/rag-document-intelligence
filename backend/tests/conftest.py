import pytest
import tempfile
import os
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

# Import your app
import sys
sys.path.append('..')
from main import app

@pytest.fixture
def client():
    """Test client for FastAPI app"""
    return TestClient(app)

@pytest.fixture
def mock_openai():
    """Mock OpenAI client for testing"""
    with patch('main.client') as mock:
        # Mock embedding response
        mock.embeddings.create.return_value = Mock(
            data=[Mock(embedding=[0.1] * 1536)]
        )
        # Mock chat completion response
        mock.chat.completions.create.return_value = Mock(
            choices=[Mock(
                message=Mock(content="Test AI response")
            )]
        )
        yield mock

@pytest.fixture
def temp_file():
    """Create temporary test file"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write("This is test document content for testing purposes.")
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.remove(temp_path)
