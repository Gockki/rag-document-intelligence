# backend/database/inspect_data.py
import psycopg2
from config import DatabaseConfig
import json
from datetime import datetime

def inspect_all_data():
    """Tarkastele kaikkea dataa PostgreSQL:ssä"""
    
    config = DatabaseConfig.from_env()
    
    try:
        conn = psycopg2.connect(
            host=config.host,
            port=config.port,
            database=config.database,
            user=config.user,
            password=config.password
        )
        
        cursor = conn.cursor()
        
        print("🔍 PostgreSQL RAG-tietokannan sisältö")
        print("=" * 60)
        
        # 1. USERS - käyttäjätiedot
        print("\n👤 USERS:")
        cursor.execute("SELECT * FROM users ORDER BY id;")
        users = cursor.fetchall()
        
        if users:
            print("   ID | Email                    | Name       | Created")
            print("   ---|--------------------------|------------|----------")
            for user in users:
                id, email, name, created_at, last_login = user
                created_str = created_at.strftime("%Y-%m-%d %H:%M") if created_at else "N/A"
                print(f"   {id:2} | {email:24} | {name:10} | {created_str}")
        else:
            print("   Ei käyttäjiä")
        
        # 2. DOCUMENTS - dokumenttien metadata
        print("\n📄 DOCUMENTS:")
        cursor.execute("""
            SELECT d.id, d.filename, d.file_size, d.chunk_count, d.processed, 
                   d.upload_time, u.name as owner
            FROM documents d
            JOIN users u ON d.user_id = u.id
            ORDER BY d.id;
        """)
        documents = cursor.fetchall()
        
        if documents:
            print("   ID | Filename         | Size | Chunks | Processed | Owner     | Uploaded")
            print("   ---|------------------|------|--------|-----------|-----------|----------")
            for doc in documents:
                id, filename, size, chunks, processed, upload_time, owner = doc
                uploaded_str = upload_time.strftime("%Y-%m-%d %H:%M") if upload_time else "N/A"
                processed_icon = "✅" if processed else "❌"
                print(f"   {id:2} | {filename:16} | {size:4} | {chunks:6} | {processed_icon:9} | {owner:9} | {uploaded_str}")
        else:
            print("   Ei dokumentteja")
        
        # 3. DOCUMENT_CHUNKS - tekstipalat
        print("\n📝 DOCUMENT_CHUNKS:")
        cursor.execute("""
            SELECT dc.id, dc.document_id, dc.chunk_index, dc.chunk_size, 
                   LEFT(dc.chunk_text, 50) as preview, d.filename
            FROM document_chunks dc
            JOIN documents d ON dc.document_id = d.id
            ORDER BY dc.document_id, dc.chunk_index;
        """)
        chunks = cursor.fetchall()
        
        if chunks:
            print("   ID | Doc | Idx | Size | Preview                                    | File")
            print("   ---|-----|-----|------|--------------------------------------------|---------")
            for chunk in chunks:
                id, doc_id, idx, size, preview, filename = chunk
                preview_clean = preview.replace('\n', ' ').replace('\r', '') if preview else ""
                print(f"   {id:2} | {doc_id:3} | {idx:3} | {size:4} | {preview_clean:42} | {filename}")
        else:
            print("   Ei dokumenttipaloja")
        
        # 4. CHAT_SESSIONS - keskustelut
        print("\n💬 CHAT_SESSIONS:")
        cursor.execute("""
            SELECT cs.id, cs.session_name, cs.created_at, cs.last_message_at, u.name as owner,
                   COUNT(cm.id) as message_count
            FROM chat_sessions cs
            JOIN users u ON cs.user_id = u.id
            LEFT JOIN chat_messages cm ON cs.id = cm.session_id
            GROUP BY cs.id, cs.session_name, cs.created_at, cs.last_message_at, u.name
            ORDER BY cs.id;
        """)
        sessions = cursor.fetchall()
        
        if sessions:
            print("   ID | Session Name         | Messages | Owner     | Created           | Last Message")
            print("   ---|----------------------|----------|-----------|-------------------|-------------------")
            for session in sessions:
                id, name, created, last_msg, owner, msg_count = session
                created_str = created.strftime("%Y-%m-%d %H:%M") if created else "N/A"
                last_str = last_msg.strftime("%Y-%m-%d %H:%M") if last_msg else "N/A"
                print(f"   {id:2} | {name:20} | {msg_count:8} | {owner:9} | {created_str} | {last_str}")
        else:
            print("   Ei chat-sessioita")
        
        # 5. CHAT_MESSAGES - viestit
        print("\n🤖 CHAT_MESSAGES:")
        cursor.execute("""
            SELECT cm.id, cm.session_id, cm.message_type, 
                   LEFT(cm.content, 60) as content_preview,
                   cm.confidence_score, cm.created_at
            FROM chat_messages cm
            ORDER BY cm.session_id, cm.created_at;
        """)
        messages = cursor.fetchall()
        
        if messages:
            print("   ID | Sess | Type      | Content Preview                                      | Conf  | Created")
            print("   ---|------|-----------|------------------------------------------------------|-------|----------")
            for msg in messages:
                id, sess_id, msg_type, content, confidence, created = msg
                created_str = created.strftime("%Y-%m-%d %H:%M") if created else "N/A"
                conf_str = f"{confidence:.2f}" if confidence else "N/A  "
                content_clean = content.replace('\n', ' ').replace('\r', '') if content else ""
                type_icon = "👤" if msg_type == "user" else "🤖"
                print(f"   {id:2} | {sess_id:4} | {type_icon} {msg_type:7} | {content_clean:52} | {conf_str} | {created_str}")
        else:
            print("   Ei viestejä")
        
        # 6. Tietokannan tilastot
        print("\n📊 TILASTOT:")
        stats_queries = [
            ("Käyttäjiä yhteensä", "SELECT COUNT(*) FROM users"),
            ("Dokumentteja yhteensä", "SELECT COUNT(*) FROM documents"),
            ("Prosessoituja dokumentteja", "SELECT COUNT(*) FROM documents WHERE processed = true"),
            ("Dokumenttipaloja yhteensä", "SELECT COUNT(*) FROM document_chunks"),
            ("Keskimääräinen palan koko", "SELECT ROUND(AVG(chunk_size)) FROM document_chunks"),
            ("Chat-sessioita", "SELECT COUNT(*) FROM chat_sessions"),
            ("Viestejä yhteensä", "SELECT COUNT(*) FROM chat_messages"),
            ("AI-vastauksia", "SELECT COUNT(*) FROM chat_messages WHERE message_type = 'assistant'"),
            ("Korkein confidence score", "SELECT ROUND(MAX(confidence_score), 3) FROM chat_messages WHERE confidence_score IS NOT NULL"),
        ]
        
        for stat_name, query in stats_queries:
            cursor.execute(query)
            result = cursor.fetchone()[0]
            print(f"   📈 {stat_name:25}: {result}")
        
        # 7. Tietokannan koko
        cursor.execute("""
            SELECT 
                schemaname,
                tablename,
                attname,
                n_distinct,
                correlation
            FROM pg_stats 
            WHERE schemaname = 'public'
            LIMIT 5;
        """)
        
        print(f"\n🗄️  TIETOKANNAN TIETOJA:")
        cursor.execute("SELECT pg_size_pretty(pg_database_size('rag_database'));")
        db_size = cursor.fetchone()[0]
        print(f"   💾 Tietokannan koko: {db_size}")
        
        cursor.close()
        conn.close()
        
        print(f"\n✅ Tarkastelu valmis!")
        print(f"🔗 Tietokanta: {config.database} @ {config.host}:{config.port}")
        
    except Exception as e:
        print(f"❌ Virhe datan tarkastelussa: {e}")

def show_full_chunks():
    """Näytä dokumenttipalat kokonaan"""
    
    config = DatabaseConfig.from_env()
    
    try:
        conn = psycopg2.connect(
            host=config.host,
            port=config.port,
            database=config.database,
            user=config.user,
            password=config.password
        )
        
        cursor = conn.cursor()
        
        print("\n📖 DOKUMENTTIPALAT KOKONAAN:")
        print("=" * 60)
        
        cursor.execute("""
            SELECT dc.chunk_index, dc.chunk_text, dc.chunk_size, d.filename
            FROM document_chunks dc
            JOIN documents d ON dc.document_id = d.id
            ORDER BY d.filename, dc.chunk_index;
        """)
        
        chunks = cursor.fetchall()
        current_file = None
        
        for chunk_idx, chunk_text, chunk_size, filename in chunks:
            if filename != current_file:
                print(f"\n📄 {filename}:")
                current_file = filename
            
            print(f"\n   🔸 Pala {chunk_idx} ({chunk_size} merkkiä):")
            print(f"   \"{chunk_text}\"")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Virhe: {e}")

if __name__ == "__main__":
    print("🔍 PostgreSQL RAG-datan tarkastelu\n")
    
    # Näytä yleiskatsaus
    inspect_all_data()
    
    # Näytä dokumenttipalat kokonaan
    show_full_chunks()
    
    print(f"\n💡 Vinkki: Kokeile myös SQL-komentoja suoraan:")
    print(f"   docker exec -it postgres-rag psql -U rag_user -d rag_database")