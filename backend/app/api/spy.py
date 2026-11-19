from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import SpyInvestigationBrief, SpyInvestigationOut
from ..services.spy import SpyError, SpyService
from .plants import ALLOWED_IMAGES

router = APIRouter(prefix="/api/spy", tags=["botanical-spy"])


@router.post("/investigations", response_model=SpyInvestigationOut, status_code=201,
             summary="Начать расследование по фото (загрузка или фото растения из коллекции)")
async def create_investigation(
    file: UploadFile | None = File(None, description="Фото JPEG/PNG/WebP до 10 МБ"),
    plant_id: int | None = Form(None, description="Привязать к растению коллекции"),
    use_plant_photo: bool = Form(False, description="Использовать фото выбранного растения"),
    force_demo: bool = Form(False),
    db: Session = Depends(get_db),
):
    data = None
    if file is not None and file.filename:
        if (file.content_type or "") not in ALLOWED_IMAGES:
            raise HTTPException(415, "Поддерживаются JPEG, PNG и WebP")
        data = await file.read()
    try:
        return SpyService(db).investigate(data, plant_id, use_plant_photo, force_demo)
    except SpyError as e:
        raise HTTPException(e.status_code, str(e))


@router.get("/investigations", response_model=list[SpyInvestigationBrief], summary="История расследований")
def list_investigations(plant_id: int | None = None, limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    return SpyService(db).history(plant_id, limit)


@router.get("/investigations/{inv_id}", response_model=SpyInvestigationOut, summary="Досье расследования")
def get_investigation(inv_id: int, db: Session = Depends(get_db)):
    try:
        return SpyService(db).get(inv_id)
    except SpyError as e:
        raise HTTPException(e.status_code, str(e))
