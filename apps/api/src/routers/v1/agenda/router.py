from typing import Annotated

from fastapi import APIRouter, Depends, Query

from auth import require_api_key
from crud import agenda
from dependencies import DatabaseSession
from api_models.agenda import AgendaTodayResponse

router = APIRouter(
    prefix="/agenda",
    tags=["agenda"],
    dependencies=[Depends(require_api_key)],
)


@router.get("/today", response_model=AgendaTodayResponse)
def today_agenda(
    session: DatabaseSession,
    hours: Annotated[int, Query(ge=1, le=168)] = agenda.DEFAULT_EVENT_HOURS,
    due_soon_days: Annotated[int, Query(ge=1, le=90)] = (agenda.DEFAULT_DUE_SOON_DAYS),
) -> AgendaTodayResponse:
    return agenda.get_today_agenda(
        session=session,
        hours=hours,
        due_soon_days=due_soon_days,
    )
