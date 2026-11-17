from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..schemas import ConsultIn, ConsultOut
from ..services.ai.service import AIService
from ..services.plants import get_plant

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.post("/consult", response_model=ConsultOut, summary="Консультация AI по выбранному растению")
def consult(req: ConsultIn, db: Session = Depends(get_db)):
    plant = get_plant(db, req.plant_id)
    try:
        return AIService(db).consult(plant, req)
    except LookupError as e:
        raise HTTPException(404, str(e))


@router.get("/status", summary="Режим AI")
def status():
    s = get_settings()
    return {"mode": s.effective_ai_mode, "configured_mode": s.ai_mode,
            "model": s.claude_model if s.effective_ai_mode == "claude" else None,
            "api_key_configured": bool(s.anthropic_api_key)}
