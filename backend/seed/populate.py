import asyncio
import json
import os
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import engine, Base, SessionLocal
from app.models.protocol import Protocol
from app.models.symptom import SymptomReport

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

async def populate_db():
    await init_db()
    async with SessionLocal() as session:
        # Load sample protocol data to create a draft protocol
        protocol_path = os.path.join(os.path.dirname(__file__), "protocole_reeducation.json")
        with open(protocol_path, "r", encoding="utf-8") as f:
            protocol_data = json.load(f)
            
        p = Protocol(
            id="protocol_demo_001",
            patient_id="pt_demo_001",
            status="draft",
            version=1,
            content_hash="mock_hash",
            content=protocol_data
        )
        session.add(p)
        
        # Load ordonnance
        ordo_path = os.path.join(os.path.dirname(__file__), "ordonnance_chirurgien.json")
        with open(ordo_path, "r", encoding="utf-8") as f:
            ordo_data = json.load(f)
            
        # Create a symptom report mock
        s = SymptomReport(
            id="report_001",
            patient_id="pt_demo_001",
            reporter_id="pt_demo_001",
            raw_text="J'ai très mal ce soir et mon genou est rouge.",
            emoji_code="unwell",
            pain_score=8,
            extraction_status="completed"
        )
        session.add(s)
        
        await session.commit()
        print("Database populated with seed data successfully!")

if __name__ == "__main__":
    asyncio.run(populate_db())
