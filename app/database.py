from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite:///./agent.db"
# DATABASE_URL = "sqlite:////tmp/agent.db"

# check_same_thread: False es necesario para evitar errores si hay varias peticiones web simultáneas.
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True) # El email no se puede repetir
    google_token = Column(Text) 
    preferences = Column(String, default="")
    conversation_history = Column(Text, default="")  # Historial de conversación reciente (JSON)

def init_db():
    """Crea las tablas en el archivo si no existen."""
    Base.metadata.create_all(bind=engine)