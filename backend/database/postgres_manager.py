# backend/database/postgres_manager.py
import psycopg2
from psycopg2.extras import RealDictCursor
from .config import DatabaseConfig
from typing import Optional, List, Dict, Any
from datetime import datetime
import json

class PostgresManager:
    """Hallinnoi PostgreSQL-operaatioita"""
    
    def __init__(self):
        self.config = DatabaseConfig.from_env()
    
    def get_connection(self):
        """Luo tietokantayhteys"""
        return psycopg2.connect(
            host=self.config.host,
            port=self.config.port,
            database=self.config.database,
            user=self.config.user,
            password=self.config.password,
            cursor_factory=RealDictCursor  # Palauttaa dict:ejä
        )
    
    # USER OPERATIONS
    def get_or_create_user(self, email: str, name: str = None) -> int:
        """Hae tai luo käyttäjä"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                # Yritä hakea olemassa oleva
                cursor.execute(
                    "SELECT id FROM users WHERE email = %s",
                    (email,)
                )
                result = cursor.fetchone()
                
                if result:
                    # Päivitä last_login
                    cursor.execute(
                        "UPDATE users SET last_login = NOW() WHERE id = %s",
                        (result['id'],)
                    )
                    return result['id']
                else:
                    # Luo uusi käyttäjä
                    cursor.execute(
                        "INSERT INTO users (email, name) VALUES (%s, %s) RETURNING id",
                        (email, name or email.split('@')[0])
                    )
                    return cursor.fetchone()['id']
    
    # DOCUMENT OPERATIONS
    def save_document_metadata(self, filename: str, original_filename: str, 
                             file_size: int, file_type: str, user_id: int, 
                             chunk_count: int) -> int:
        """Tallenna dokumentin metadata"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO documents 
                    (filename, original_filename, file_size, file_type, user_id, processed, chunk_count)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (filename, original_filename, file_size, file_type, user_id, True, chunk_count))
                
                return cursor.fetchone()['id']
    
    def save_document_chunks(self, document_id: int, chunks: List[str]):
        """Tallenna dokumentin tekstipalat"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                for i, chunk in enumerate(chunks):
                    cursor.execute("""
                        INSERT INTO document_chunks 
                        (document_id, chunk_index, chunk_text, chunk_size)
                        VALUES (%s, %s, %s, %s)
                    """, (document_id, i, chunk, len(chunk)))
    
    def get_documents_by_user(self, user_id: int) -> List[Dict[str, Any]]:
        """Hae käyttäjän dokumentit (vanha metodi)"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id, filename, original_filename, file_size, 
                        upload_time, chunk_count, processed
                    FROM documents 
                    WHERE user_id = %s 
                    ORDER BY upload_time DESC
                """, (user_id,))
                
                return cursor.fetchall()
    
    # Lisää nämä funktiot postgres_manager.py tiedostoon DOCUMENT OPERATIONS -osion alle

    def delete_document(self, doc_id: int) -> bool:
        """Poista dokumentti ja kaikki siihen liittyvä data"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Poista ensin chat-viestien viittaukset dokumenttiin
                    # (jos source_documents sisältää doc_id:n)
                    cursor.execute("""
                        UPDATE chat_messages 
                        SET source_documents = NULL
                        WHERE source_documents::jsonb @> %s
                    """, (json.dumps([doc_id]),))
                    
                    # Poista dokumentin palaset
                    cursor.execute("DELETE FROM document_chunks WHERE document_id = %s", (doc_id,))
                    
                    # Poista itse dokumentti
                    cursor.execute("DELETE FROM documents WHERE id = %s", (doc_id,))
                    
                    conn.commit()
                    
                    print(f"✅ Document {doc_id} deleted from PostgreSQL")
                    return True
                    
        except Exception as e:
            print(f"❌ Error deleting document {doc_id}: {e}")
            return False

    def get_document_owner(self, doc_id: int) -> Optional[int]:
        """Hae dokumentin omistaja turvallisuustarkistusta varten"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT user_id FROM documents WHERE id = %s", (doc_id,))
                    result = cursor.fetchone()
                    
                    return result['user_id'] if result else None
                    
        except Exception as e:
            print(f"Error getting document owner: {e}")
            return None

    def get_document_info(self, doc_id: int) -> Optional[Dict[str, Any]]:
        """Hae yksittäisen dokumentin tiedot"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT 
                            d.id,
                            d.filename,
                            d.original_filename,
                            d.file_size,
                            d.file_type,
                            d.chunk_count,
                            d.processed,
                            d.upload_time,
                            d.user_id,
                            u.email as user_email,
                            u.name as user_name
                        FROM documents d
                        JOIN users u ON d.user_id = u.id
                        WHERE d.id = %s
                    """, (doc_id,))
                    
                    return cursor.fetchone()
                    
        except Exception as e:
            print(f"Error getting document info: {e}")
            return None

    # Päivitä get_user_documents funktiota palauttamaan dict eikä tuple
    def get_user_documents(self, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
    
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        id, 
                        filename, 
                        original_filename, 
                        chunk_count, 
                        upload_time, 
                        file_size,
                        COALESCE(file_type, 'text/plain') as file_type,
                        processed
                    FROM documents 
                    WHERE user_id = %s 
                    ORDER BY upload_time DESC 
                    LIMIT %s
                """, (user_id, limit))
                            
                documents = cursor.fetchall()
                
                return documents if documents else []
    
    # CHAT OPERATIONS
    def create_chat_session(self, user_id: int, session_name: str = None) -> int:
        """Luo uusi chat-sessio"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                if not session_name:
                    session_name = f"Keskustelu {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                
                cursor.execute("""
                    INSERT INTO chat_sessions (user_id, session_name)
                    VALUES (%s, %s)
                    RETURNING id
                """, (user_id, session_name))
                
                return cursor.fetchone()['id']
    
    def save_chat_message(self, session_id: int, message_type: str, content: str,
                        confidence_score: float = None, source_documents: List[int] = None):
        """Tallenna chat-viesti (vanha metodi)"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                source_docs_json = json.dumps(source_documents) if source_documents else None
                
                cursor.execute("""
                    INSERT INTO chat_messages 
                    (session_id, message_type, content, confidence_score, source_documents)
                    VALUES (%s, %s, %s, %s, %s)
                """, (session_id, message_type, content, confidence_score, source_docs_json))
                
                # Päivitä session viimeinen viesti aika
                cursor.execute("""
                    UPDATE chat_sessions 
                    SET last_message_at = NOW() 
                    WHERE id = %s
                """, (session_id,))
    
    def save_message(self, session_id: int, message_type: str, content: str, confidence_score: float = None) -> int:
        """Tallenna viesti ja palauta message ID (uusi main.py:lle)"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO chat_messages 
                    (session_id, message_type, content, confidence_score, source_documents)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                """, (session_id, message_type, content, confidence_score, None))
                
                message_id = cursor.fetchone()['id']
                
                # Päivitä session viimeinen viesti aika
                cursor.execute("""
                    UPDATE chat_sessions 
                    SET last_message_at = NOW() 
                    WHERE id = %s
                """, (session_id,))
                
                return message_id
    
    def get_chat_history(self, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Hae käyttäjän chat-historia (vanha metodi)"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        cs.id as session_id,
                        cs.session_name,
                        cm.message_type,
                        cm.content,
                        cm.confidence_score,
                        cm.source_documents,
                        cm.created_at
                    FROM chat_sessions cs
                    JOIN chat_messages cm ON cs.id = cm.session_id
                    WHERE cs.user_id = %s
                    ORDER BY cm.created_at DESC
                    LIMIT %s
                """, (user_id, limit))
                
                return cursor.fetchall()
    
    def get_recent_sessions(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Hae viimeisimmät chat-sessiot (vanha metodi)"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        cs.id,
                        cs.session_name,
                        cs.created_at,
                        cs.last_message_at,
                        COUNT(cm.id) as message_count
                    FROM chat_sessions cs
                    LEFT JOIN chat_messages cm ON cs.id = cm.session_id
                    WHERE cs.user_id = %s
                    GROUP BY cs.id, cs.session_name, cs.created_at, cs.last_message_at
                    ORDER BY cs.last_message_at DESC
                    LIMIT %s
                """, (user_id, limit))
                
                return cursor.fetchall()
    
    def get_user_chat_sessions(self, user_id: int, limit: int = 20) -> List[tuple]:
        """Hae käyttäjän chat-sessiot (uusi main.py:lle)"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        cs.id,
                        cs.session_name,
                        cs.created_at,
                        cs.last_message_at,
                        COUNT(cm.id) as message_count
                    FROM chat_sessions cs
                    LEFT JOIN chat_messages cm ON cs.id = cm.session_id
                    WHERE cs.user_id = %s
                    GROUP BY cs.id, cs.session_name, cs.created_at, cs.last_message_at
                    ORDER BY COALESCE(cs.last_message_at, cs.created_at) DESC
                    LIMIT %s
                """, (user_id, limit))
                
                return cursor.fetchall()
    
    def get_session_messages(self, session_id: int, limit: int = 50) -> List[tuple]:
        """Hae session viestit (uusi main.py:lle)"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        cm.session_id,
                        cs.session_name,
                        cm.message_type,
                        cm.content,
                        cm.confidence_score,
                        cm.created_at
                    FROM chat_messages cm
                    JOIN chat_sessions cs ON cm.session_id = cs.id
                    WHERE cm.session_id = %s
                    ORDER BY cm.created_at ASC
                    LIMIT %s
                """, (session_id, limit))
                
                return cursor.fetchall()
    
    def get_user_messages(self, user_id: int, limit: int = 50) -> List[tuple]:
        """Hae käyttäjän kaikki viestit (uusi main.py:lle)"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        cm.session_id,
                        cs.session_name,
                        cm.message_type,
                        cm.content,
                        cm.confidence_score,
                        cm.created_at
                    FROM chat_messages cm
                    JOIN chat_sessions cs ON cm.session_id = cs.id
                    WHERE cs.user_id = %s
                    ORDER BY cm.created_at DESC
                    LIMIT %s
                """, (user_id, limit))
                
                return cursor.fetchall()
    
    # ANALYTICS & STATS
    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """Hae käyttäjän tilastot"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        COUNT(DISTINCT d.id) as total_documents,
                        SUM(d.chunk_count) as total_chunks,
                        COUNT(DISTINCT cs.id) as total_sessions,
                        COUNT(cm.id) as total_messages,
                        AVG(cm.confidence_score) as avg_confidence
                    FROM users u
                    LEFT JOIN documents d ON u.id = d.user_id
                    LEFT JOIN chat_sessions cs ON u.id = cs.user_id  
                    LEFT JOIN chat_messages cm ON cs.id = cm.session_id AND cm.message_type = 'assistant'
                    WHERE u.id = %s
                    GROUP BY u.id
                """, (user_id,))
                
                result = cursor.fetchone()
                return dict(result) if result else {}

# Test the manager
if __name__ == "__main__":
    print("🧪 Testataan PostgresManager...")
    
    manager = PostgresManager()
    
    # Testaa käyttäjä
    user_id = manager.get_or_create_user("test@example.com", "Test User")
    print(f"✅ User ID: {user_id}")
    
    # Testaa dokumentti
    doc_id = manager.save_document_metadata(
        "test_doc.txt", "Test Document.txt", 1024, "text/plain", user_id, 2
    )
    print(f"✅ Document ID: {doc_id}")
    
    # Testaa chat (vanha metodi)
    session_id = manager.create_chat_session(user_id)
    print(f"✅ Session ID: {session_id}")
    
    manager.save_chat_message(session_id, "user", "Testikysymys")
    manager.save_chat_message(session_id, "assistant", "Testivastaus", 0.95, [doc_id])
    
    # Testaa chat (uusi metodi)
    msg_id = manager.save_message(session_id, "user", "Uusi testikysymys")
    print(f"✅ Message ID: {msg_id}")
    
    # Testaa dokumenttien haku
    docs = manager.get_user_documents(user_id, 10)
    print(f"✅ Found {len(docs)} documents")
    
    # Testaa chat-sessiot
    sessions = manager.get_user_chat_sessions(user_id, 5)
    print(f"✅ Found {len(sessions)} chat sessions")
    
    # Hae tilastot
    stats = manager.get_user_stats(user_id)
    print(f"📊 User stats: {stats}")
    
    print("🎉 PostgresManager toimii!")