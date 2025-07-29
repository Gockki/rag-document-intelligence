# backend/database/config.py
import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class DatabaseConfig:
    """PostgreSQL connection configuration"""
    host: str = "localhost"
    port: int = 5432
    database: str = "rag_database"
    user: str = "rag_user"
    password: str = "rag_password"
    
@classmethod
def from_env(cls) -> 'DatabaseConfig':
    # Railway käyttää DATABASE_URL:ia
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        # Parse DATABASE_URL: postgresql://user:pass@host:port/db
        import urllib.parse
        parsed = urllib.parse.urlparse(database_url)
        return cls(
            host=parsed.hostname,
            port=parsed.port or 5432,
            database=parsed.path[1:],  # Remove leading /
            user=parsed.username,
            password=parsed.password
        )
    
    # Fallback erilliset muuttujat
    return cls(
        host=os.getenv("DATABASE_HOST", "localhost"),
        port=int(os.getenv("DATABASE_PORT", "5432")),
        database=os.getenv("DATABASE_NAME", "railway"),
        user=os.getenv("DATABASE_USER", "postgres"),
        password=os.getenv("DATABASE_PASSWORD", "")
    )
    
    @property
    def connection_string(self) -> str:
        """Get PostgreSQL connection string"""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"

# Test connection function
def test_connection(config: Optional[DatabaseConfig] = None) -> bool:
    """Test PostgreSQL connection"""
    import psycopg2
    
    if config is None:
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
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        print(f"✅ PostgreSQL connection successful!")
        print(f"📋 Version: {version[:50]}...")
        return True
        
    except Exception as e:
        print(f"❌ PostgreSQL connection failed: {e}")
        return False

if __name__ == "__main__":
    # Test the connection
    test_connection()