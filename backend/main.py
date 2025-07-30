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
chroma_client = chromadb.PersistentClient(path="/data/chroma_db")
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
    bot_mode: Optional[str] = "friendly"  # LISÄTTY: Bot personality mode

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
        
        # PÄIVITETTY: Bot personality system prompts
        if request.bot_mode == "friendly":
            system_prompt = """Olet DocBot, ystävällinen ja innostunut AI-assistentti 🤖

PERSOONALLISUUS:
- Innostunut datasta ja uusista löydöksistä
- Käytä emojeja luonnollisesti (📊 📈 ✨ 🎯 💡)
- Jaa "ajatuksiasi": "Vau!", "Mielenkiintoista!", "Huomasin että..."
- Ole kannustava ja positiivinen

VASTAUSTYYLI:
1. Anna ensin selkeä vastaus kysymykseen
2. Lisää oma havaintosi tai reaktio
3. Ehdota mitä voisi tutkia seuraavaksi

ERIKOISUUDET eri tiedostotyypeille:
- 📊 Excel: "Näissä numeroissa on mielenkiintoinen trendi..."
- 📄 PDF: "Dokumentissa mainitaan kiinnostavasti..."
- 📝 Teksti: "Tekstistä nousee esiin..."

Esimerkki: "Liikevaihto oli 2.5M€ viime vuonna. 📈 Vau, kasvua peräti 45%! Erityisesti Q4 näyttää todella vahvalta. Haluaisitko että tutkin tarkemmin, mikä ajoi tämän loistavan kasvun?"

Vastaa aina suomeksi."""

        elif request.bot_mode == "analytical":
            system_prompt = """Olet erittäin analyyttinen AI-tutkija, joka keskittyy syvälliseen data-analyysiin.

PERSOONALLISUUS:
- Tarkka ja yksityiskohtainen
- Etsi korrelaatioita, trendejä ja poikkeamia
- Käytä tilastollisia termejä
- Kyseenalaista ja pohdi syy-seuraussuhteita

VASTAUSTYYLI:
1. Tarkka data ja numerot
2. Tilastollinen analyysi tai trendi
3. Hypoteesit ja mahdolliset selitykset

ERIKOISUUDET:
- 📊 Excel: Laske keskiarvoja, kasvuprosentteja, korrelaatioita
- 📄 PDF: Analysoi dokumentin rakennetta ja argumentteja
- 📝 Teksti: Tunnista teemat ja yhteydet

Esimerkki: "Liikevaihto: 2,500,000€ (YoY kasvu: 45.3%). Keskimääräinen kuukausikasvu 3.2%, keskihajonta 1.8%. Q4 poikkeaa merkittävästi (+2.3σ). Korrelaatio markkinointikulujen kanssa: 0.87. Hypoteesi: Q4 kampanja tuotti poikkeuksellisen ROI:n."

Vastaa aina suomeksi ja ole erittäin tarkka."""

        elif request.bot_mode == "creative":
            system_prompt = """Olet luova AI-ajattelija, joka näkee asiat uudesta näkökulmasta 🎨

PERSOONALLISUUS:
- Käytä metaforia ja vertauksia
- Yhdistä asioita yllättävästi
- Näe isompi kuva ja piilotetut yhteydet
- Ole inspiroiva ja visionäärinen

VASTAUSTYYLI:
1. Vastaa kysymykseen
2. Tarjoa luova näkökulma tai vertaus
3. "Mitä jos..." -ajattelu

ERIKOISUUDET:
- 📊 Excel: "Numerot kertovat tarinan..."
- 📄 PDF: "Dokumentti on kuin kartta..."
- 📝 Teksti: "Sanat muodostavat kuvion..."

Esimerkki: "Liikevaihto oli 2.5M€ - kuin vuori, joka on kasvanut 45% korkeammaksi! 🏔️ Jokainen numero on asiakkaan luottamuksen osoitus. Q4 oli kuin raketti, joka laukaistiin tähtiin. Mitä jos ensi vuonna tavoittelisimme kuuta?"

Vastaa aina suomeksi ja ole inspiroiva."""

        else:  # professional mode
            system_prompt = """Olet konsulttimainen AI-analyytikko, joka tarjoaa eksekutiivitason näkemyksiä.

PERSOONALLISUUS:
- Ammattimainen ja asiallinen
- Executive summary -tyylinen
- Keskity liiketoimintavaikutuksiin
- Anna konkreettisia toimintasuosituksia

VASTAUSTYYLI:
1. Suora vastaus avainlukuineen
2. Liiketoimintavaikutukset
3. Selkeät toimintasuositukset

ERIKOISUUDET:
- 📊 Excel: KPI-analyysi ja suorituskyvyn mittarit
- 📄 PDF: Strategiset havainnot ja yhteenveto
- 📝 Teksti: Keskeiset toimenpide-ehdotukset

Esimerkki: "Liikevaihto: €2.5M (kasvu: 45% YoY). Avaintekijä: Q4 suorituskyky ylitti tavoitteet 23%. Suositus: 1) Skaalaa Q4 toimintamalli muihin kvartaaleihin, 2) Allokoi 15% budjetista vastaaviin kasvualoitteisiin, 3) Aseta tavoite: €3.6M seuraavalle vuodelle."

Vastaa aina suomeksi ja ole ytimekäs."""
        
        # LISÄTTY: Temperature map for different modes
        temperature_map = {
            "friendly": 0.5,      # Hieman luovempi
            "analytical": 0.2,    # Tarkka
            "creative": 0.8,      # Luova
            "professional": 0.3   # Kontrolloitu
        }
        
        # Generate response using OpenAI
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Konteksti dokumenteista:\n{context}\n\nKysymys: {request.question}"}
            ],
            temperature=temperature_map.get(request.bot_mode, 0.3)  # PÄIVITETTY: Dynamic temperature
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
async def list_all_user_documents(user_email: str = "demo@example.com"):
    """Listaa käyttäjän kaikki dokumentit (turvallinen versio)"""
    try:
        print(f"📄 Fetching documents for: {user_email}")
        user_id = postgres_manager.get_or_create_user(user_email)
        print(f"👤 User ID: {user_id}")
        
        documents = postgres_manager.get_user_documents(user_id)
        print(f"📚 Found {len(documents)} documents")
        
        # Muunna lista dict-muotoon jos tarpeen
        doc_list = []
        for doc in documents:
            if isinstance(doc, dict):
                doc_list.append(doc)
            else:
                # Jos RealDictRow, muunna dict:iksi
                doc_list.append(dict(doc))
        
        # Lisää tieto siitä, onko dokumentilla embeddings ChromaDB:ssä
        for doc in doc_list:
            try:
                # Tarkista ChromaDB turvallisesti
                doc["has_embeddings"] = False  # Oletusarvo
                
                if collection:  # Varmista että collection on olemassa
                    chroma_results = collection.get(
                        where={"doc_id": doc["id"]},
                        limit=1
                    )
                    
                    # Tarkista että tulokset ovat valideja
                    if chroma_results and isinstance(chroma_results, dict):
                        ids = chroma_results.get("ids", [])
                        if ids and isinstance(ids, list):
                            doc["has_embeddings"] = len(ids) > 0
                            
            except Exception as e:
                print(f"⚠️ ChromaDB check failed for doc {doc.get('id', '?')}: {e}")
                # Jos ChromaDB haku epäonnistuu, jatka silti
                pass
        
        return {
            "documents": doc_list,
            "total": len(doc_list),
            "user_email": user_email
        }
        
    except Exception as e:
        print(f"❌ Error listing documents: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

        
    except Exception as e:
        print(f"Error listing documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: int,
    user_email: str = "demo@example.com"
):
    """Poista dokumentti (vain omistaja voi poistaa)"""
    try:
        # Tarkista käyttäjän oikeudet
        user_id = postgres_manager.get_or_create_user(user_email)
        doc_owner_id = postgres_manager.get_document_owner(doc_id)
        
        if not doc_owner_id:
            raise HTTPException(status_code=404, detail="Document not found")
            
        if doc_owner_id != user_id:
            raise HTTPException(
                status_code=403, 
                detail="You don't have permission to delete this document"
            )
        
        # Hae dokumentin tiedot ennen poistoa (lokitusta varten)
        doc_info = postgres_manager.get_document_info(doc_id)
        
        # Poista ChromaDB:stä
        print(f"🗑️ Deleting document {doc_id} from ChromaDB...")
        try:
            # Poista kaikki dokumentin chunkit ChromaDB:stä
            collection.delete(where={"doc_id": doc_id})
            print(f"✅ Deleted embeddings for document {doc_id}")
        except Exception as e:
            print(f"⚠️ Warning: Failed to delete from ChromaDB: {e}")
            # Jatka silti PostgreSQL poistoon
        
        # Poista PostgreSQL:stä
        print(f"🗑️ Deleting document {doc_id} from PostgreSQL...")
        success = postgres_manager.delete_document(doc_id)
        
        if success:
            return {
                "message": f"Document '{doc_info['original_filename']}' deleted successfully",
                "doc_id": doc_id,
                "filename": doc_info['original_filename']
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to delete document from database"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting document: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/documents/{doc_id}/info")
async def get_document_info(
    doc_id: int,
    user_email: str = "demo@example.com"
):
    """Hae yksittäisen dokumentin tiedot"""
    try:
        # Tarkista käyttäjän oikeudet
        user_id = postgres_manager.get_or_create_user(user_email)
        doc_info = postgres_manager.get_document_info(doc_id)
        
        if not doc_info:
            raise HTTPException(status_code=404, detail="Document not found")
            
        if doc_info['user_id'] != user_id:
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to view this document"
            )
        
        # Hae chunk-määrä ChromaDB:stä
        chroma_results = collection.get(where={"doc_id": doc_id})
        doc_info["embeddings_count"] = len(chroma_results["ids"])
        
        return doc_info
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting document info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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