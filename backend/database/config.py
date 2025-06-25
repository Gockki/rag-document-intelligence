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
        """Load database config from environment variables"""
        return cls(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            database=os.getenv("DB_NAME", "rag_database"),
            user=os.getenv("DB_USER", "rag_user"),
            password=os.getenv("DB_PASSWORD", "rag_password")
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