from fastapi import Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Plant
from ..services.plants import get_plant


def plant_dep(plant_id: int, db: Session = Depends(get_db)) -> Plant:
    return get_plant(db, plant_id)
