from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime
from app.db.session import Base

class FuelPrice(Base):
    __tablename__ = "fuel_prices"

    id = Column(Integer, primary_key=True, index=True)
    fuel_type = Column(String(50), unique=True)  # e.g., "Petrol", "Diesel"
    price = Column(Float)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    source = Column(String(100), nullable=True)
