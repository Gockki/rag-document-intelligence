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

# UUSI: Document processing
from document_processors import process_file_by_type

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Enhanced Document Intelligence Platform",
    description="RAG-powered document analysis with Excel, PDF & Data Analytics",
    version="3.0.0"
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
    user_email: Optional[str] = "demo@example.com"
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
    file_type: str = "unknown"
    has_numerical_data: bool = False

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
    """Enhanced text chunking with overlap"""
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # Excel-taulukoille: yritä löytää taulukon loppu
        if "===" in text[start:end]:
            table_end = text.find("===", end)
            if table_end != -1 and table_end - start < chunk_size * 1.5:
                end = table_end
        
        # Try to break at sentence boundary
        elif end < len(text):
            for i in range(end, max(start + chunk_size - 200, start), -1):
                if text[i] in '.!?\n':
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
        "message": "Enhanced Document Intelligence Platform API v3.0",
        "status": "running",
        "features": ["RAG", "PostgreSQL", "ChromaDB", "Excel Analytics", "PDF Processing"],
        "supported_formats": ["TXT", "MD", "PDF", "XLSX", "XLS"],
        "version": "3.0.0"
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
        "postgresql_users": postgres_users,
        "supported_formats": ["TXT", "MD", "PDF", "XLSX", "XLS"]
    }

@app.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    user_email: str = "demo@example.com"
):
    """Enhanced upload with Excel, PDF & Text support"""
    try:
        print(f"📁 Processing file: {file.filename} (type: {file.content_type}) for user: {user_email}")
        
        # Get or create user
        user_id = postgres_manager.get_or_create_user(user_email)
        print(f"👤 User ID: {user_id}")
        
        # Read file content
        content = await file.read()
        file_size = len(content)
        print(f"📄 File size: {file_size} bytes")
        
        # Process file by type
        processed_text, metadata = process_file_by_type(content, file.filename, file.content_type or '')
        print(f"🔧 File processed: {metadata}")
        
        # Check for processing errors
        if 'error' in metadata:
            raise HTTPException(status_code=400, detail=f"File processing failed: {metadata['error']}")
        
        # Chunk the processed text (larger chunks for Excel data)
        chunk_size = 1500 if metadata.get('file_type') == 'excel' else 1000
        chunks = chunk_text(processed_text, chunk_size=chunk_size, overlap=300)
        print(f"✂️ Created {len(chunks)} chunks (size: {chunk_size})")
        
        # Save document metadata to PostgreSQL
        doc_id = postgres_manager.save_document_metadata(
            filename=file.filename,
            original_filename=file.filename,
            file_size=file_size,
            file_type=metadata.get('file_type', 'unknown'),
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
            
            chroma_id = f"doc_{doc_id}_chunk_{i}"
            
            collection.add(
                embeddings=[embedding],
                documents=[chunk],
                metadatas=[{
                    "source": file.filename,
                    "chunk_id": i,
                    "doc_id": doc_id,
                    "user_id": user_id,
                    "file_size": file_size,
                    "file_type": metadata.get('file_type', 'unknown'),
                    "has_numerical_data": metadata.get('has_analytics', False)
                }],
                ids=[chroma_id]
            )
        
        print(f"🔍 {len(chunks)} embeddings stored in ChromaDB")
        
        return {
            "message": f"Document '{file.filename}' processed successfully!",
            "document_id": doc_id,
            "chunks_created": len(chunks),
            "file_type": metadata.get('file_type'),
            "has_numerical_data": metadata.get('has_analytics', False),
            "supported_formats": ["TXT", "MD", "PDF", "XLSX", "XLS"],
            "processing_details": {
                "file_type": metadata.get('file_type'),
                "sheets": metadata.get('sheets', []) if metadata.get('file_type') == 'excel' else None,
                "pages": metadata.get('page_count') if metadata.get('file_type') == 'pdf' else None,
                "character_count": metadata.get('character_count'),
                "has_numerical_data": metadata.get('has_analytics', False)
            }
        }
        
    except Exception as e:
        print(f"❌ Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.post("/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    """Enhanced query with Excel/PDF awareness"""
    try:
        print(f"❓ Query: '{request.question}' for user: {request.user_email}")
        
        # Get or create user
        user_id = postgres_manager.get_or_create_user(request.user_email)
        
        # Get or create chat session
        if request.session_id:
            session_id = request.session_id
        else:
            session_id = postgres_manager.create_chat_session(
                user_id=user_id,
                session_name=f"Chat {request.question[:20]}..."
            )
        
        # Generate query embedding
        query_embedding = get_embedding(request.question)
        print(f"🔍 Query embedding generated")
        
        # Search in ChromaDB
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=request.max_results,
            where={"user_id": user_id}
        )
        
        if not results['documents'][0]:
            return QueryResponse(
                answer="En löydä relevanttia tietoa ladatuista dokumenteista. Lataa ensin dokumentteja (Excel, PDF tai tekstitiedostoja) ja yritä uudelleen.",
                sources=[],
                confidence=0.0,
                session_id=session_id,
                message_id=0
            )
        
        # Prepare context with file type awareness
        context_parts = []
        sources = []
        
        for i, (doc, metadata, distance) in enumerate(zip(
            results['documents'][0], 
            results['metadatas'][0], 
            results['distances'][0]
        )):
            confidence = max(0, 1 - distance)
            
            # Add file type context
            file_type = metadata.get("file_type", "unknown")
            source_prefix = {
                "excel": "📊 Excel-taulukko",
                "pdf": "📄 PDF-dokumentti", 
                "text": "📝 Tekstitiedosto"
            }.get(file_type, "📄 Dokumentti")
            
            context_parts.append(f"{source_prefix} ({metadata.get('source', 'Unknown')}): {doc}")
            
            sources.append({
                "source": metadata.get("source", "Unknown"),
                "chunk_id": metadata.get("chunk_id", i),
                "confidence": round(confidence, 3),
                "file_type": file_type,
                "has_numerical_data": metadata.get("has_numerical_data", False)
            })
        
        context = "\n\n".join(context_parts)
        
        # Enhanced system prompt for different file types
        system_prompt = """Olet asiantunteva dokumenttianalysaattori. Vastaa kysymyksiin perustuen annettuihin dokumentteihin.

ERIKOISUUDET eri tiedostotyypeille:
- 📊 Excel-tiedostot: Korosta numeerista dataa, tilastoja ja trendejä. Anna tarkkoja lukuja.
- 📄 PDF-dokumentit: Huomioi dokumentin rakenne ja sivunumerot.
- 📝 Tekstitiedostot: Keskity sisältöön ja kontekstiin.

VASTAUSTYYLI:
- Anna selkeitä, faktapohjaisia vastauksia
- Mainitse lähdetiedoston nimi ja tyyppi
- Jos kyse on numeroista, anna tarkat arvot
- Jos data on Excel-taulukosta, mainitse mahdolliset laskelmat

Vastaa aina suomeksi ja ole tarkka."""
        
        # Generate response using OpenAI
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Konteksti dokumenteista:\n{context}\n\nKysymys: {request.question}"}
            ],
            temperature=0.3
        )
        
        answer = response.choices[0].message.content
        avg_confidence = sum(source["confidence"] for source in sources) / len(sources)
        
        # Save to chat history
        postgres_manager.save_message(session_id, "user", request.question)
        message_id = postgres_manager.save_message(session_id, "assistant", answer, avg_confidence)
        
        print(f"✅ Query processed successfully, confidence: {avg_confidence:.3f}")
        
        return QueryResponse(
            answer=answer,
            sources=sources,
            confidence=round(avg_confidence, 3),
            session_id=session_id,
            message_id=message_id
        )
        
    except Exception as e:
        print(f"❌ Query error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

@app.get("/documents")
async def list_documents(user_email: str = "demo@example.com", limit: int = 50):
    """List user's documents with enhanced info"""
    try:
        print(f"🔍 DEBUG: Starting list_documents for {user_email}")
        user_id = postgres_manager.get_or_create_user(user_email)
        print(f"🔍 DEBUG: user_id = {user_id}")
        
        documents = postgres_manager.get_user_documents(user_id, limit)
        print(f"🔍 DEBUG: documents count = {len(documents)}")
        print(f"🔍 DEBUG: first doc = {documents[0] if documents else 'None'}")
        if documents:
            print(f"🔍 DEBUG: first doc length = {len(documents[0])}")
            print(f"🔍 DEBUG: first doc fields = {[type(field) for field in documents[0]]}")
        
        return {
            "documents": [
                DocumentInfo(
                    id=doc['id'],                    # Muutettu doc[0] → doc['id']
                    filename=doc['filename'],        # Muutettu doc[1] → doc['filename']
                    original_filename=doc['original_filename'],  # doc[2] → doc['original_filename']
                    chunk_count=doc['chunk_count'],  # doc[3] → doc['chunk_count']
                    upload_time=doc['upload_time'].isoformat(),  # doc[4] → doc['upload_time']
                    file_size=doc['file_size'],      # doc[5] → doc['file_size']
                    file_type=doc['file_type'] or "unknown",     # doc[6] → doc['file_type']
                    has_numerical_data=doc['has_numerical_data'] or False  # doc[7] → doc['has_numerical_data']
                )
                for doc in documents
            ],
            "total": len(documents),
            "supported_formats": ["TXT", "MD", "PDF", "XLSX", "XLS"]
        }
    except Exception as e:
        print(f"❌ Documents error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")

@app.get("/chat/sessions")
async def get_chat_sessions(user_email: str = "demo@example.com", limit: int = 20):
    """Get user's chat sessions"""
    try:
        user_id = postgres_manager.get_or_create_user(user_email)
        sessions = postgres_manager.get_user_chat_sessions(user_id, limit)
        
        return {
            "sessions": [
                {
                    "session_id": session['id'],                    # session[0] → session['id']
                    "session_name": session['session_name'],       # session[1] → session['session_name']
                    "created_at": session['created_at'].isoformat(),   # session[2] → session['created_at']
                    "last_message_at": session['last_message_at'].isoformat() if session['last_message_at'] else None,  # session[3]
                    "message_count": session['message_count']      # session[4] → session['message_count']
                }
                for session in sessions
            ],
            "total": len(sessions)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get sessions: {str(e)}")

@app.get("/chat/history")
async def get_chat_history(user_email: str = "demo@example.com", session_id: Optional[int] = None, limit: int = 50):
    """Get chat history for user or specific session"""
    try:
        user_id = postgres_manager.get_or_create_user(user_email)
        
        if session_id:
            messages = postgres_manager.get_session_messages(session_id, limit)
        else:
            messages = postgres_manager.get_user_messages(user_id, limit)
        
        return {
            "messages": [
                ChatHistory(
                    session_id=msg['session_id'],           # msg[0] → msg['session_id']
                    session_name=msg['session_name'],       # msg[1] → msg['session_name']
                    message_type=msg['message_type'],       # msg[2] → msg['message_type']
                    content=msg['content'],                 # msg[3] → msg['content']
                    confidence_score=msg['confidence_score'], # msg[4] → msg['confidence_score']
                    created_at=msg['created_at'].isoformat()  # msg[5] → msg['created_at']
                )
                for msg in messages
            ],
            "total": len(messages)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get chat history: {str(e)}")
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)