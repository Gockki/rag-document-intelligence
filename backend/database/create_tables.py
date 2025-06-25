# backend/database/create_tables.py
import psycopg2
from config import DatabaseConfig

def create_tables():
    """Luo RAG-järjestelmän tietokantataulut"""
    
    # Lataa konfiguraatio
    config = DatabaseConfig.from_env()
    
    try:
        # Yhdistä tietokantaan
        conn = psycopg2.connect(
            host=config.host,
            port=config.port,
            database=config.database,
            user=config.user,
            password=config.password
        )
        
        cursor = conn.cursor()
        
        print("🏗️  Luodaan RAG-järjestelmän taulut...")
        
        # 1. Users taulu - käyttäjätiedot
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                name VARCHAR(255),
                created_at TIMESTAMP DEFAULT NOW(),
                last_login TIMESTAMP
            );
        """)
        print("✅ Users taulu luotu")
        
        # 2. Documents taulu - dokumenttien metadata
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id SERIAL PRIMARY KEY,
                filename VARCHAR(255) NOT NULL,
                original_filename VARCHAR(255),
                file_size INTEGER,
                file_type VARCHAR(50),
                upload_time TIMESTAMP DEFAULT NOW(),
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                processed BOOLEAN DEFAULT FALSE,
                chunk_count INTEGER DEFAULT 0
            );
        """)
        print("✅ Documents taulu luotu")
        
        # 3. Document chunks taulu - dokumenttien palat tekstinä
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS document_chunks (
                id SERIAL PRIMARY KEY,
                document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
                chunk_index INTEGER NOT NULL,
                chunk_text TEXT NOT NULL,
                chunk_size INTEGER,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
        print("✅ Document_chunks taulu luotu")
        
        # 4. Chat sessions taulu - keskusteluhistoria
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                session_name VARCHAR(255),
                created_at TIMESTAMP DEFAULT NOW(),
                last_message_at TIMESTAMP DEFAULT NOW()
            );
        """)
        print("✅ Chat_sessions taulu luotu")
        
        # 5. Chat messages taulu - kysymykset ja vastaukset
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id SERIAL PRIMARY KEY,
                session_id INTEGER REFERENCES chat_sessions(id) ON DELETE CASCADE,
                message_type VARCHAR(20) NOT NULL, -- 'user' tai 'assistant'
                content TEXT NOT NULL,
                confidence_score FLOAT,
                source_documents TEXT, -- JSON array dokumentti-ID:istä
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
        print("✅ Chat_messages taulu luotu")
        
        # Tallenna muutokset
        conn.commit()
        
        # Näytä luodut taulut
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        
        tables = cursor.fetchall()
        print("\n📋 Tietokannan taulut:")
        for table in tables:
            print(f"   📊 {table[0]}")
        
        # Näytä taulujen rakenne
        print("\n🔍 Taulujen rakenteet:")
        for table in tables:
            table_name = table[0]
            cursor.execute(f"""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_name = '{table_name}'
                ORDER BY ordinal_position;
            """)
            columns = cursor.fetchall()
            print(f"\n📊 {table_name.upper()}:")
            for col_name, data_type, is_nullable in columns:
                nullable = "NULL" if is_nullable == "YES" else "NOT NULL"
                print(f"   • {col_name}: {data_type} ({nullable})")
        
        cursor.close()
        conn.close()
        
        print(f"\n🎉 Kaikki taulut luotu onnistuneesti!")
        print(f"🔗 Tietokanta: {config.database} @ {config.host}:{config.port}")
        
    except Exception as e:
        print(f"❌ Virhe taulujen luonnissa: {e}")
        return False
    
    return True

def insert_test_data():
    """Lisää testidataa tauluihin"""
    
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
        
        print("\n🧪 Lisätään testidataa...")
        
        # Lisää testikäyttäjä
        cursor.execute("""
            INSERT INTO users (email, name) 
            VALUES (%s, %s) 
            ON CONFLICT (email) DO NOTHING
            RETURNING id;
        """, ("jere.kokki@gmail.com", "Jere Kokki"))
        
        result = cursor.fetchone()
        if result:
            user_id = result[0]
            print(f"✅ Käyttäjä lisätty: ID {user_id}")
        else:
            # Hae olemassaoleva käyttäjä
            cursor.execute("SELECT id FROM users WHERE email = %s", ("jere.kokki@gmail.com",))
            user_id = cursor.fetchone()[0]
            print(f"ℹ️  Käyttäjä oli jo olemassa: ID {user_id}")
        
        # Lisää testidokumentti
        cursor.execute("""
            INSERT INTO documents (filename, original_filename, file_size, file_type, user_id, processed, chunk_count)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
        """, ("test_document.txt", "Testidokumentti.txt", 1024, "text/plain", user_id, True, 2))
        
        doc_id = cursor.fetchone()[0]
        print(f"✅ Testidokumentti lisätty: ID {doc_id}")
        
        # Lisää testipaloja
        cursor.execute("""
            INSERT INTO document_chunks (document_id, chunk_index, chunk_text, chunk_size)
            VALUES (%s, %s, %s, %s);
        """, (doc_id, 0, "Tämä on ensimmäinen dokumenttipala. Se sisältää tärkeää tietoa RAG-järjestelmästä.", 88))
        
        cursor.execute("""
            INSERT INTO document_chunks (document_id, chunk_index, chunk_text, chunk_size)
            VALUES (%s, %s, %s, %s);
        """, (doc_id, 1, "Toinen dokumenttipala jatkaa ensimmäistä. PostgreSQL integraatio on mielenkiintoinen aihe.", 95))
        
        print("✅ Dokumenttipalat lisätty")
        
        # Lisää testisessio
        cursor.execute("""
            INSERT INTO chat_sessions (user_id, session_name)
            VALUES (%s, %s)
            RETURNING id;
        """, (user_id, "Ensimmäinen keskustelu"))
        
        session_id = cursor.fetchone()[0]
        print(f"✅ Chat-sessio luotu: ID {session_id}")
        
        # Lisää testiviestit
        cursor.execute("""
            INSERT INTO chat_messages (session_id, message_type, content)
            VALUES (%s, %s, %s);
        """, (session_id, "user", "Mikä on RAG-järjestelmä?"))
        
        cursor.execute("""
            INSERT INTO chat_messages (session_id, message_type, content, confidence_score, source_documents)
            VALUES (%s, %s, %s, %s, %s);
        """, (session_id, "assistant", "RAG (Retrieval-Augmented Generation) on järjestelmä joka yhdistää tiedonhaun ja generatiivisen AI:n.", 0.95, f'[{doc_id}]'))
        
        print("✅ Testiviestit lisätty")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("\n🎉 Testidata lisätty onnistuneesti!")
        
    except Exception as e:
        print(f"❌ Virhe testidatan lisäämisessä: {e}")
        return False
    
    return True

def query_test_data():
    """Hae ja näytä testidata"""
    
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
        
        print("\n📊 Testidatan haku...")
        
        # Hae käyttäjät ja heidän dokumenttinsa
        cursor.execute("""
            SELECT 
                u.name,
                u.email,
                d.filename,
                d.chunk_count,
                d.upload_time
            FROM users u
            LEFT JOIN documents d ON u.id = d.user_id
            ORDER BY u.name, d.upload_time;
        """)
        
        print("\n👤 Käyttäjät ja dokumentit:")
        for row in cursor.fetchall():
            name, email, filename, chunk_count, upload_time = row
            if filename:
                print(f"   {name} ({email})")
                print(f"     📄 {filename} - {chunk_count} palaa - {upload_time}")
            else:
                print(f"   {name} ({email}) - Ei dokumentteja")
        
        # Hae chat-historia
        cursor.execute("""
            SELECT 
                cs.session_name,
                cm.message_type,
                cm.content,
                cm.confidence_score,
                cm.created_at
            FROM chat_sessions cs
            JOIN chat_messages cm ON cs.id = cm.session_id
            ORDER BY cs.id, cm.created_at;
        """)
        
        print("\n💬 Chat-historia:")
        current_session = None
        for row in cursor.fetchall():
            session_name, msg_type, content, confidence, created_at = row
            if session_name != current_session:
                print(f"\n   🗨️  {session_name}:")
                current_session = session_name
            
            icon = "👤" if msg_type == "user" else "🤖"
            conf_text = f" (confidence: {confidence:.2f})" if confidence else ""
            print(f"     {icon} {content}{conf_text}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Virhe datan haussa: {e}")

if __name__ == "__main__":
    print("🐘 PostgreSQL RAG-taulujen luonti alkaa...\n")
    
    # 1. Luo taulut
    if create_tables():
        print("\n" + "="*50)
        
        # 2. Lisää testidata
        if insert_test_data():
            print("\n" + "="*50)
            
            # 3. Hae ja näytä data
            query_test_data()
    
    print(f"\n🎉 PostgreSQL setup valmis!")