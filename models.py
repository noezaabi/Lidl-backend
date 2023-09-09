from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.engine import URL
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import dotenv_values
config = dotenv_values(".env")

db_url = config.get("DB_URL")
if not db_url:
    raise ValueError("DB_URL is not set in .env file")

engine = create_engine(db_url)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    sender = Column(String)
    message = Column(String)
    response = Column(String)
    
class Item(Base):
    __tablename__ = 'Item'

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    stripePriceId = Column(String, nullable=False)


Base.metadata.create_all(engine)
