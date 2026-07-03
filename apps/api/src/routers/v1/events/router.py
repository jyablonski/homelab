from typing import Annotated

from fastapi import APIRouter, Depends, Query

from auth import require_api_key
from crud import agenda
from api_models.agenda import EventsUpcomingResponse

router = APIRouter(
    prefix="/events",
    tags=["events"],
    dependencies=[Depends(require_api_key)],
)


@router.get("/upcoming", response_model=EventsUpcomingResponse)
def upcoming_events(
    hours: Annotated[int, Query(ge=1, le=168)] = agenda.DEFAULT_EVENT_HOURS,
) -> EventsUpcomingResponse:
    return agenda.get_upcoming_events(hours=hours)
