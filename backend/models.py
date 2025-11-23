"""
Database models for fermenter monitoring system.
"""
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()


class Measurement(Base):
    """Represents a single sensor measurement."""
    __tablename__ = 'measurements'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    tag = Column(String(100), nullable=False, index=True)
    value = Column(Float, nullable=False)
    is_anomaly = Column(Boolean, default=False, nullable=False)
    
    def __repr__(self):
        return f"<Measurement(tag='{self.tag}', value={self.value}, timestamp={self.timestamp}, is_anomaly={self.is_anomaly})>"


# Database setup utilities
def init_database(db_url='sqlite:///sensor_data.db'):
    """Initialize the database and create all tables."""
    engine = create_engine(db_url, echo=False)
    Base.metadata.create_all(engine)
    return engine


def get_session(engine):
    """Create and return a database session."""
    Session = sessionmaker(bind=engine)
    return Session()
