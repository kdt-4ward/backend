from services.openai_client import call_openai_completion
from models.db_models import AIChatSummary, CoupleChatSummary
from core.db import SessionLocal
from datetime import datetime

async def summarize_ai_chat(user_id: str, couple_id: str, reference: list, target: list) -> str:
    # 프롬프트 구성
    ref_text = "\n".join([f"{h['role']}: {h['content']}" for h in reference])
    tgt_messages = "\n".join([f"{h['role']}: {h['content']}" for h in target])

    messages = [
        {"role": "system", "content": "너는 심리 상담 요약가야."},
        {"role": "user", "content": f"다음은 이전 대화 내용이야 (참고용):\n{ref_text}"},
        {"role": "user", "content": f"다음은 최근 대화 내용이야 (요약용):\n{tgt_messages}"},
        {"role": "user", "content": "위 이전 대화의 맥락을 고려하여 최근 대화를 요약해줘."}
    ]

    summary = await call_openai_completion(messages)

    db = SessionLocal()
    db.add(AIChatSummary(
        user_id=user_id,
        couple_id=couple_id,
        summary=summary,
        created_at=datetime.utcnow()
    ))
    db.commit()
    db.close()
    return summary

async def summarize_couple_chat(couple_id: str, reference: list, target: list) -> str:
    # 1. 프롬프트에 넣을 이전 대화 요약 (참고용)
    ref_text = "\n".join([f"{h['user_id']}: {h['content']}" for h in reference])

    # 2. 요약 대상 대화
    tgt_messages = [{"role": "user", "content": h["content"]} for h in target]

    # 3. GPT 요청용 메시지 구성
    messages = [
        {"role": "system", "content": "너는 커플 상담 전문가야."},
        {"role": "user", "content": f"다음은 참고용 과거 대화야:\n{ref_text}"},
        *tgt_messages,
        {"role": "user", "content": "이전 맥락을 참고하여 최신 대화를 요약해줘. 주요 감정, 갈등, 변화 등을 중심으로 간결하게 정리해줘."}
    ]

    summary = await call_openai_completion(messages)

    db = SessionLocal()
    db.add(CoupleChatSummary(
        couple_id=couple_id,
        summary=summary,
        created_at=datetime.utcnow()
    ))
    db.commit()
    db.close()
    return summary