from sqlalchemy.orm import Session

from ...config import get_settings
from ...models import AIConsultation, Fertilizer, Plant
from ...schemas import ConsultIn, ConsultOut
from ..fertilizer import assess
from .claude_engine import ClaudeEngine, ClaudeUnavailable
from .context import build_context
from .demo_engine import DemoEngine, detect_topic


class AIService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    def consult(self, plant: Plant, req: ConsultIn) -> ConsultOut:
        ctx = build_context(self.db, plant)
        topic = req.topic if req.topic != "general" else detect_topic(req.question)
        assessment = None
        if req.fertilizer_id is not None:
            fert = self.db.get(Fertilizer, req.fertilizer_id)
            if fert is None:
                raise LookupError("Удобрение не найдено")
            assessment = assess(self.db, plant, fert)
            topic = "fertilizer"

        demo = DemoEngine().answer(ctx, topic, req.question, assessment)
        mode, model, answer, warnings = "demo", None, demo["answer"], list(demo["warnings"])
        if self.settings.effective_ai_mode == "claude" and not req.force_demo:
            try:
                answer = ClaudeEngine(self.settings).answer(
                    ctx, topic, req.question, [h.model_dump() for h in req.history],
                    assessment.model_dump() if assessment else None)
                mode, model = "claude", self.settings.claude_model
            except ClaudeUnavailable as e:
                warnings.insert(0, f"Claude недоступен ({e}); показан ответ Demo AI Mode.")

        rec = AIConsultation(plant_id=plant.id, topic=topic, question=req.question, answer=answer, mode=mode,
                             model=model, context_snapshot=ctx)
        self.db.add(rec)
        self.db.commit()
        return ConsultOut(consultation_id=rec.id, plant_id=plant.id, topic=topic, mode=mode, model=model,
                          answer=answer, clarifying_questions=demo["clarifying_questions"],
                          data_used=demo["data_used"], missing_data=demo["missing_data"], warnings=warnings,
                          created_at=rec.created_at)
