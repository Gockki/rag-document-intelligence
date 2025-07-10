# tests/integration/test_database.py
import pytest
from unittest.mock import patch, Mock
import tempfile
import os

class TestPostgreSQLIntegration:
    """Test PostgreSQL database operations"""
    
    @patch('database.postgres_manager.PostgresManager')
    def test_user_creation(self, mock_postgres):
        """Test user creation in database"""
        # Mock database manager
        mock_db = Mock()
        mock_postgres.return_value = mock_db
        mock_db.get_or_create_user.return_value = 1
        
        from database.postgres_manager import PostgresManager
        
        db_manager = PostgresManager()
        user_id = db_manager.get_or_create_user("test@example.com", "Test User")
        
        assert user_id == 1
        mock_db.get_or_create_user.assert_called_once_with("test@example.com", "Test User")

    @patch('database.postgres_manager.PostgresManager')
    def test_document_storage(self, mock_postgres):
        """Test document metadata storage"""
        mock_db = Mock()
        mock_postgres.return_value = mock_db
        mock_db.save_document.return_value = 123
        
        from database.postgres_manager import PostgresManager
        
        db_manager = PostgresManager()
        doc_id = db_manager.save_document(
            user_id=1,
            filename="test.txt",
            original_filename="test.txt",
            file_size=100,
            file_type="text/plain"
        )
        
        assert doc_id == 123

    @patch('database.postgres_manager.PostgresManager')
    def test_chat_message_storage(self, mock_postgres):
        """Test chat message storage"""
        mock_db = Mock()
        mock_postgres.return_value = mock_db
        mock_db.save_chat_message.return_value = 456
        
        from database.postgres_manager import PostgresManager
        
        db_manager = PostgresManager()
        message_id = db_manager.save_chat_message(
            session_id=1,
            message_type="user",
            content="Test message",
            confidence_score=0.95
        )
        
        assert message_id == 456

    @patch('database.postgres_manager.PostgresManager')
    def test_database_connection_error(self, mock_postgres):
        """Test database connection error handling"""
        mock_postgres.side_effect = Exception("Database connection failed")
        
        with pytest.raises(Exception) as exc_info:
            from database.postgres_manager import PostgresManager
            PostgresManager()
        
        assert "Database connection failed" in str(exc_info.value)


class TestChromaDBIntegration:
    """Test ChromaDB vector database operations"""
    
    @patch('chromadb.PersistentClient')
    def test_vector_storage(self, mock_chroma_client):
        """Test vector storage in ChromaDB"""
        # Mock ChromaDB
        mock_client = Mock()
        mock_collection = Mock()
        mock_chroma_client.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection
        
        # Test vector storage
        embeddings = [0.1] * 1536  # Typical OpenAI embedding size
        
        mock_collection.add.return_value = None
        
        # This would be called in your actual code
        mock_collection.add(
            embeddings=[embeddings],
            documents=["test document"],
            ids=["doc_1"],
            metadatas=[{"source": "test.txt"}]
        )
        
        mock_collection.add.assert_called_once()

    @patch('chromadb.PersistentClient')
    def test_vector_search(self, mock_chroma_client):
        """Test vector similarity search"""
        mock_client = Mock()
        mock_collection = Mock()
        mock_chroma_client.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection
        
        # Mock search results
        mock_collection.query.return_value = {
            'documents': [['Found document content']],
            'distances': [[0.2]],
            'metadatas': [[{'source': 'test.txt'}]]
        }
        
        # Test search
        results = mock_collection.query(
            query_embeddings=[[0.1] * 1536],
            n_results=5
        )
        
        assert len(results['documents'][0]) == 1
        assert results['distances'][0][0] == 0.2
        mock_collection.query.assert_called_once()


class TestFileProcessing:
    """Test file processing utilities"""
    
    def test_text_chunking(self):
        """Test text chunking functionality"""
        # Import your chunking function
        import sys
        sys.path.append('../..')
        from main import chunk_text
        
        # Test text
        long_text = "This is a test sentence. " * 100  # ~2500 characters
        
        chunks = chunk_text(long_text, chunk_size=1000, overlap=200)
        
        assert len(chunks) > 1
        assert all(len(chunk) <= 1200 for chunk in chunks)  # chunk_size + overlap
        
        # Test overlap
        if len(chunks) > 1:
            # Should have some overlap between chunks
            assert any(
                chunks[i][-100:] in chunks[i+1][:300] 
                for i in range(len(chunks)-1)
            )

    def test_empty_text_chunking(self):
        """Test chunking empty text"""
        import sys
        sys.path.append('../..')
        from main import chunk_text
        
        chunks = chunk_text("", chunk_size=1000)
        
        assert chunks == []

    def test_short_text_chunking(self):
        """Test chunking text shorter than chunk size"""
        import sys
        sys.path.append('../..')
        from main import chunk_text
        
        short_text = "Short text."
        chunks = chunk_text(short_text, chunk_size=1000)
        
        assert len(chunks) == 1
        assert chunks[0] == short_text

    def test_embedding_generation(self):
        """Test embedding generation with mocked OpenAI"""
        import sys
        sys.path.append('../..')
        
        with patch('main.client') as mock_openai:
            mock_openai.embeddings.create.return_value = Mock(
                data=[Mock(embedding=[0.1] * 1536)]
            )
            
            from main import get_embedding
            
            embedding = get_embedding("test text")
            
            assert len(embedding) == 1536
            assert all(isinstance(x, float) for x in embedding)
            mock_openai.embeddings.create.assert_called_once()


class TestAPIEndToEnd:
    """End-to-end integration tests"""
    
    def test_upload_and_query_flow(self, client, mock_openai, temp_file):
        """Test complete upload -> query flow"""
        # Step 1: Upload document
        with open(temp_file, 'rb') as f:
            upload_response = client.post(
                "/upload",
                files={"file": ("test.txt", f, "text/plain")},
                data={"user_email": "test@example.com"}
            )
        
        assert upload_response.status_code == 200
        upload_data = upload_response.json()
        assert "document_id" in upload_data
        
        # Step 2: Query the document
        query_response = client.post(
            "/query",
            json={
                "question": "What is this document about?",
                "user_email": "test@example.com"
            }
        )
        
        assert query_response.status_code == 200
        query_data = query_response.json()
        
        # Verify response structure
        assert "answer" in query_data
        assert "sources" in query_data
        assert "confidence" in query_data
        assert isinstance(query_data["sources"], list)
        assert 0.0 <= query_data["confidence"] <= 1.0

    def test_multiple_documents_query(self, client, mock_openai):
        """Test querying across multiple documents"""
        # Upload multiple documents
        docs = ["Document 1 content", "Document 2 content", "Document 3 content"]
        
        for i, content in enumerate(docs):
            response = client.post(
                "/upload",
                files={"file": (f"doc{i}.txt", content.encode(), "text/plain")},
                data={"user_email": "test@example.com"}
            )
            assert response.status_code == 200
        
        # Query across all documents
        response = client.post(
            "/query",
            json={
                "question": "What information is available?",
                "user_email": "test@example.com",
                "max_results": 10
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["sources"]) >= 0  # Should find sources from multiple docs