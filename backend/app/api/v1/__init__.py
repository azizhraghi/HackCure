from fastapi import APIRouter
from . import chat, documents, checkin

router = APIRouter()
router.include_router(chat.router, tags=["chat"])
router.include_router(documents.router, tags=["documents"])
router.include_router(checkin.router, tags=["checkin"])
