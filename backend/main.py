# backend/main.py
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
import chromadb
import os
from typing import List, Optional
import uvicorn
from dotenv import load_dotenv

# PostgreSQL integration
from database.postgres_manager import PostgresManager

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Document Intelligence Platform",
    description="RAG-powered document analysis system with PostgreSQL",
    version="2.0.0"
)

# CORS middleware for frontend connection
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize Chroma
chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection(
    name="documents",
    metadata={"hnsw:space": "cosine"}
)

# Initialize PostgreSQL manager
postgres_manager = PostgresManager()

# Pydantic models
class QueryRequest(BaseModel):
    question: str
    max_results: Optional[int] = 5
    user_email: Optional[str] = "demo@example.com"  # Demo user
    session_id: Optional[int] = None

class QueryResponse(BaseModel):
    answer: str
    sources: List[dict]
    confidence: float
    session_id: int
    message_id: int

class DocumentInfo(BaseModel):
    id: int
    filename: str
    original_filename: str
    chunk_count: int
    upload_time: str
    file_size: int

class ChatHistory(BaseModel):
    session_id: int
    session_name: str
    message_type: str
    content: str
    confidence_score: Optional[float]
    created_at: str

# Utility functions
def get_embedding(text: str) -> List[float]:
    """Generate embedding using OpenAI API"""
    try:
        response = client.embeddings.create(
            model="text-embedding-ada-002",
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding generation failed: {str(e)}")

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """Intelligent text chunking with overlap"""
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # Try to break at sentence boundary
        if end < len(text):
            for i in range(end, max(start + chunk_size - 200, start), -1):
                if text[i] in '.!?':
                    end = i + 1
                    break
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        start = end - overlap
        
    return chunks

# API Endpoints
@app.get("/")
async def root():
    return {
        "message": "Document Intelligence Platform API v2.0",
        "status": "running",
        "features": ["RAG", "PostgreSQL", "ChromaDB", "Chat History"],
        "version": "2.0.0"
    }

@app.get("/health")
async def health_check():
    """Enhanced health check with PostgreSQL"""
    try:
        # Test OpenAI connection
        client.embeddings.create(
            model="text-embedding-ada-002",
            input="test"
        )
        openai_status = "connected"
    except:
        openai_status = "error"
    
    # Test PostgreSQL connection
    try:
        # Use PostgresManager to test connection
        test_user_id = postgres_manager.get_or_create_user("health@check.com", "Health Check")
        postgres_status = "connected"
        postgres_users = "available"
    except:
        postgres_status = "error"
        postgres_users = "unavailable"
    
    return {
        "status": "healthy",
        "openai": openai_status,
        "chroma": "connected",
        "chroma_documents": collection.count(),
        "postgresql": postgres_status,
        "postgresql_users": postgres_users
    }

@app.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    user_email: str = "demo@example.com"
):
    """Upload and process document with PostgreSQL metadata"""
    try:
        print(f"📁 Uploading file: {file.filename} for user: {user_email}")
        
        # Get or create user
        user_id = postgres_manager.get_or_create_user(user_email)
        print(f"👤 User ID: {user_id}")
        
        # Read file content
        content = await file.read()
        file_size = len(content)
        text = content.decode("utf-8")
        print(f"📄 File size: {file_size} bytes, text length: {len(text)}")
        
        # Chunk the text
        chunks = chunk_text(text)
        print(f"✂️ Created {len(chunks)} chunks")
        
        # Save document metadata to PostgreSQL
        doc_id = postgres_manager.save_document_metadata(
            filename=file.filename,
            original_filename=file.filename,
            file_size=file_size,
            file_type=file.content_type or "text/plain",
            user_id=user_id,
            chunk_count=len(chunks)
        )
        print(f"💾 Document metadata saved with ID: {doc_id}")
        
        # Save document chunks to PostgreSQL
        postgres_manager.save_document_chunks(doc_id, chunks)
        print(f"📝 Document chunks saved to PostgreSQL")
        
        # Generate embeddings and store in ChromaDB
        for i, chunk in enumerate(chunks):
            embedding = get_embedding(chunk)
            
            # Use document database ID in ChromaDB for linking
            chroma_id = f"doc_{doc_id}_chunk_{i}"
            
            collection.add(
                embeddings=[embedding],
                documents=[chunk],
                metadatas=[{
                    "source": file.filename,
                    "chunk_id": i,
                    "doc_id": doc_id,  # PostgreSQL document ID
                    "user_id": user_id,
                    "file_size": file_size
                }],
                ids=[chroma_id]
            )
            print(f"🔍 Stored embedding for chunk {i}")
        
        return {
            "message": f"Document '{file.filename}' processed successfully",
            "document_id": doc_id,
            "chunks_created": len(chunks),
            "user_id": user_id,
            "file_size": file_size
        }
        
    except Exception as e:
        print(f"❌ Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.post("/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    """Query documents using RAG with chat history"""
    try:
        print(f"🔍 Query: {request.question} from user: {request.user_email}")
        
        # Get or create user
        user_id = postgres_manager.get_or_create_user(request.user_email)
        
        # Create or get chat session
        if request.session_id:
            session_id = request.session_id
        else:
            session_id = postgres_manager.create_chat_session(user_id)
        
        print(f"💬 Using session ID: {session_id}")
        
        # Save user question to PostgreSQL
        postgres_manager.save_chat_message(
            session_id=session_id,
            message_type="user", 
            content=request.question
        )
        
        # Generate query embedding
        query_embedding = get_embedding(request.question)
        
        # Search similar chunks in ChromaDB
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=request.max_results,
            where={"user_id": user_id}  # Filter by user
        )
        
        if not results['documents'][0]:
            answer = "No relevant documents found for your query."
            confidence = 0.0
            sources = []
        else:
            # Prepare context from ChromaDB results
            context_chunks = results['documents'][0]
            sources = []
            
            for i, (doc, metadata, distance) in enumerate(zip(
                context_chunks, 
                results['metadatas'][0], 
                results['distances'][0]
            )):
                similarity = 1 - distance
                sources.append({
                    "source": metadata['source'],
                    "chunk_id": metadata['chunk_id'],
                    "doc_id": metadata['doc_id'],
                    "similarity": similarity,
                    "content_preview": doc[:100] + "..."
                })
            
            # Generate answer using GPT-4
            context = "\n\n".join([f"Source {i+1}: {chunk}" for i, chunk in enumerate(context_chunks)])
            
            prompt = f"""Based on the following context from the user's documents, answer their question accurately and helpfully.

Context:
{context}

Question: {request.question}

Answer:"""

            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that answers questions based on provided documents. Always be accurate and cite sources when relevant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.1
            )
            
            answer = response.choices[0].message.content
            
            # Calculate confidence based on similarity scores
            avg_similarity = sum(1 - d for d in results['distances'][0]) / len(results['distances'][0])
            confidence = avg_similarity
        
        # Save AI response to PostgreSQL
        source_doc_ids = [s['doc_id'] for s in sources] if sources else None
        postgres_manager.save_chat_message(
            session_id=session_id,
            message_type="assistant",
            content=answer,
            confidence_score=confidence,
            source_documents=source_doc_ids
        )
        
        print(f"💾 Chat messages saved to PostgreSQL")
        
        return QueryResponse(
            answer=answer,
            sources=sources,
            confidence=confidence,
            session_id=session_id,
            message_id=0  # Would need to get actual message ID if needed
        )
        
    except Exception as e:
        print(f"❌ Query error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

@app.get("/documents")
async def list_documents(user_email: str = "demo@example.com"):
    """List user's documents from PostgreSQL"""
    try:
        user_id = postgres_manager.get_or_create_user(user_email)
        documents = postgres_manager.get_documents_by_user(user_id)
        
        return {
            "user_email": user_email,
            "user_id": user_id,
            "documents": [
                DocumentInfo(
                    id=doc['id'],
                    filename=doc['filename'],
                    original_filename=doc['original_filename'] or doc['filename'],
                    chunk_count=doc['chunk_count'],
                    upload_time=doc['upload_time'].isoformat() if doc['upload_time'] else "",
                    file_size=doc['file_size'] or 0
                )
                for doc in documents
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")

@app.get("/chat/history")
async def get_chat_history(user_email: str = "demo@example.com", limit: int = 50):
    """Get user's chat history from PostgreSQL"""
    try:
        user_id = postgres_manager.get_or_create_user(user_email)
        history = postgres_manager.get_chat_history(user_id, limit)
        
        return {
            "user_email": user_email,
            "user_id": user_id,
            "messages": [
                ChatHistory(
                    session_id=msg['session_id'],
                    session_name=msg['session_name'],
                    message_type=msg['message_type'],
                    content=msg['content'],
                    confidence_score=msg['confidence_score'],
                    created_at=msg['created_at'].isoformat() if msg['created_at'] else ""
                )
                for msg in history
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get chat history: {str(e)}")

@app.get("/chat/sessions")
async def get_chat_sessions(user_email: str = "demo@example.com", limit: int = 10):
    """Get user's recent chat sessions"""
    try:
        user_id = postgres_manager.get_or_create_user(user_email)
        sessions = postgres_manager.get_recent_sessions(user_id, limit)
        
        return {
            "user_email": user_email,
            "user_id": user_id,
            "sessions": sessions
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get chat sessions: {str(e)}")

@app.get("/stats")
async def get_user_stats(user_email: str = "demo@example.com"):
    """Get user statistics from PostgreSQL"""
    try:
        user_id = postgres_manager.get_or_create_user(user_email)
        stats = postgres_manager.get_user_stats(user_id)
        
        return {
            "user_email": user_email,
            "user_id": user_id,
            "stats": stats
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user stats: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)