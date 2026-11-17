"""Claude-движок. Ключ API читается только на сервере (ANTHROPIC_API_KEY в backend/.env)."""
import json

import anthropic

from ...config import Settings

SYSTEM_PROMPT = """Ты — консультант по уходу за комнатными орхидеями в приложении Smart Orchid.
Отвечай на русском, дружелюбно и по делу, в Markdown с разделами:
«Что я вижу в данных», «Анализ», «Рекомендации», «Уточняющие вопросы», и, если нужно, «⚠️ Важно» и «Каких данных нет».

Правила:
- Опирайся только на переданный JSON-контекст растения. Не придумывай измерения, даты и события, которых нет.
  Если показатель в missing_measurements — прямо скажи, что данных нет, и не делай по нему выводов.
- Различай: измерения (measured), расчётные показатели (derived), прогнозы (forecast), наблюдения пользователя
  (observation) и твои гипотезы. Гипотезы помечай словами «вероятно», «возможно».
- Если data_source = demo, упомяни, что данные демонстрационные.
- Учитывай вид, стадию развития, сезон (season_note), состояние корней и листьев, историю поливов и подкормок.
- Задавай 2–4 уточняющих вопроса, когда данных недостаточно для уверенного вывода.
- Удобрения: не назначай препарат сам, не придумывай составы и дозировки. Оценивай только то удобрение,
  которое указал пользователь; дозировку определяет инструкция производителя. Если корни повреждены или есть
  признаки обезвоживания — не рекомендуй подкормку без дополнительной оценки.
  Если в контексте есть fertilizer_assessment (оценка по правилам), объясни её и не противоречь блокирующим условиям.
- Болезни: не ставь диагноз по датчикам; перечисли, какие визуальные признаки проверить, и предложи
  обратиться к специалисту при серьёзных симптомах.
- Не выдавай медицинских/химических инструкций сверх инструкции производителя."""


class ClaudeUnavailable(Exception):
    pass


class ClaudeEngine:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key, max_retries=2, timeout=90.0)

    def answer(self, ctx: dict, topic: str, question: str, history: list[dict],
               assessment: dict | None = None) -> str:
        payload = dict(ctx)
        if assessment:
            payload["fertilizer_assessment"] = assessment
        context_msg = ("Контекст растения (JSON):\n```json\n" + json.dumps(payload, ensure_ascii=False, default=str)
                       + f"\n```\nТема: {topic}")
        messages = [{"role": "user", "content": context_msg},
                    {"role": "assistant", "content": "Контекст получен. Готов ответить на вопрос о растении."}]
        messages += [{"role": h["role"], "content": h["content"]} for h in history]
        messages.append({"role": "user", "content": question})
        try:
            response = self.client.beta.messages.create(
                model=self.settings.claude_model,
                max_tokens=16000,
                system=SYSTEM_PROMPT,
                messages=messages,
                output_config={"effort": self.settings.claude_effort},
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
        except anthropic.AuthenticationError as e:
            raise ClaudeUnavailable("Неверный ANTHROPIC_API_KEY") from e
        except anthropic.RateLimitError as e:
            raise ClaudeUnavailable("Превышен лимит запросов к Claude API") from e
        except anthropic.APIStatusError as e:
            raise ClaudeUnavailable(f"Claude API вернул ошибку {e.status_code}") from e
        except anthropic.APIConnectionError as e:
            raise ClaudeUnavailable("Нет соединения с Claude API") from e
        if response.stop_reason == "refusal":
            raise ClaudeUnavailable("Claude отклонил запрос")
        text = "".join(b.text for b in response.content if b.type == "text").strip()
        if not text:
            raise ClaudeUnavailable("Пустой ответ Claude")
        return text
