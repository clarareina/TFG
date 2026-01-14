from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.orm import sessionmaker, declarative_base

# Conexión a SQLite
DATABASE_URL = "sqlite:///./agent.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# TABLA DE USUARIOS
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    # Aquí guardamos TODO el token junto (como un JSON gigante)
    google_token = Column(Text) 

def init_db():
    Base.metadata.create_all(bind=engine)