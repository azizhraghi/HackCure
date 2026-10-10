from fastapi import APIRouter
from . import chat
# We can import symptoms, protocols, etc here

router = APIRouter()
router.include_router(chat.router, tags=["chat"])
