# backend/main.py
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
import openai
import chromadb
from chromadb.config import Settings
import os
from dotenv import load_dotenv
from typing import List, Optional
import uvicorn

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Document Intelligence Platform",
    description="RAG-powered document analysis system",
    version="1.0.0"
)

# CORS middleware for frontend connection
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize Chroma
chroma_client = chromadb.PersistentClient(path="./chroma_db")

# Get or create collection
collection = chroma_client.get_or_create_collection(
    name="documents",
    metadata={"hnsw:space": "cosine"}
)

# Pydantic models
class QueryRequest(BaseModel):
    question: str
    max_results: Optional[int] = 5

class QueryResponse(BaseModel):
    answer: str
    sources: List[dict]
    confidence: float

class DocumentInfo(BaseModel):
    id: str
    filename: str
    chunk_count: int
    upload_time: str

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
            # Look for sentence endings
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
        "message": "Document Intelligence Platform API",
        "status": "running",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test OpenAI connection
        client.embeddings.create(
            model="text-embedding-ada-002",
            input="test"
        )
        openai_status = "connected"
    except:
        openai_status = "error"
    
    return {
        "status": "healthy",
        "openai": openai_status,
        "chroma": "connected",
        "documents": collection.count()
    }

@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload and process document"""
    try:
        
        # Read file content
        content = await file.read()
        
        text = content.decode("utf-8")
        
        
        # Chunk the text
        chunks = chunk_text(text)
        
        
        # Generate embeddings and store
        doc_id = file.filename.split('.')[0]
        
        
        for i, chunk in enumerate(chunks):
            
            embedding = get_embedding(chunk)
            
            
            collection.add(
                embeddings=[embedding],
                documents=[chunk],
                metadatas=[{
                    "source": file.filename,
                    "chunk_id": i,
                    "doc_id": doc_id
                }],
                ids=[f"{doc_id}_chunk_{i}"]
            )
            
        
        return {
            "message": f"Document '{file.filename}' processed successfully",
            "chunks_created": len(chunks),
            "document_id": doc_id
        }
        
    except Exception as e:
        
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.post("/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    """Query documents using RAG"""
    try:
        # Generate query embedding
        query_embedding = get_embedding(request.question)
        
        # Search similar chunks
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=request.max_results
        )
        
        if not results['documents'][0]:
            return QueryResponse(
                answer="No relevant documents found.",
                sources=[],
                confidence=0.0
            )
        
        # Prepare context
        context_chunks = results['documents'][0]
        sources = []
        
        for i, (doc, metadata) in enumerate(zip(context_chunks, results['metadatas'][0])):
            sources.append({
                "source": metadata['source'],
                "chunk_id": metadata['chunk_id'],
                "similarity": 1 - results['distances'][0][i],  # Convert distance to similarity
                "content_preview": doc[:100] + "..."
            })
        
        # Generate answer using GPT-4
        context = "\n\n".join([f"Source {i+1}: {chunk}" for i, chunk in enumerate(context_chunks)])
        
        prompt = f"""Based on the following context, answer the user's question. Be specific and cite sources when possible.

Context:
{context}

Question: {request.question}

Answer:"""

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that answers questions based on provided documents. Always cite your sources and be accurate."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.1
        )
        
        answer = response.choices[0].message.content
        
        # Calculate confidence based on similarity scores
        avg_similarity = sum(1 - d for d in results['distances'][0]) / len(results['distances'][0])
        
        return QueryResponse(
            answer=answer,
            sources=sources,
            confidence=avg_similarity
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

@app.get("/documents", response_model=List[DocumentInfo])
async def list_documents():
    """List all uploaded documents"""
    try:
        # Get all documents from collection
        all_docs = collection.get()
        
        # Group by document
        docs_info = {}
        for metadata in all_docs['metadatas']:
            doc_id = metadata['doc_id']
            if doc_id not in docs_info:
                docs_info[doc_id] = {
                    "id": doc_id,
                    "filename": metadata['source'],
                    "chunk_count": 0,
                    "upload_time": "2024-01-01"  # Would be actual timestamp in production
                }
            docs_info[doc_id]["chunk_count"] += 1
        
        return list(docs_info.values())
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)