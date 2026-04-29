from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from database import get_db_session

DatabaseSession = Annotated[Session, Depends(get_db_session)]
