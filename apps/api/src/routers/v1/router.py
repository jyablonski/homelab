from fastapi import APIRouter

from routers.v1.agenda.router import router as agenda_router
from routers.v1.events.router import router as events_router
from routers.v1.reminders.router import router as reminders_router

router = APIRouter(prefix="/v1")
router.include_router(agenda_router)
router.include_router(events_router)
router.include_router(reminders_router)
