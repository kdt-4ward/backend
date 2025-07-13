from services.openai_client import call_openai_completion
from models.db_tables import AIChatSummary, CoupleChatSummary
from db.db import SessionLocal
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

async def summarize_ai_chat(prev_summary: str, target: list) -> str:
    """
    누적 요약 방식: 이전 summary(요약) + 최근 미요약 메시지(target)만 받아
    전체 누적 요약을 새로 만듭니다.
    """

    # 이전 누적 요약이 없을 때는 빈 문자열 처리
    prev_summary_text = prev_summary if prev_summary else "(없음)"
    target_text = "\n".join([f"{h['role']}: {h['content']}" for h in target])

    prompt = f"""
[Previous Summary]
{prev_summary_text}

[Recent Conversation]
{target_text}

Based on both of these,
1) Update the cumulative summary in no more than 7 sentences.
3) Always summarize in the same language user uses.
"""

    messages = [
        {"role": "system", "content": "Below is a record of actual conversation between a user and you. 'user:' is the user's message, 'assistant:' is your reply."},
        {"role": "user", "content": prompt.strip()}
    ]
    logger.info(f"[aichat_summarize] input: {messages}")
    summary, _ = await call_openai_completion(messages)

    return summary

async def summarize_couple_chat(couple_id: str, reference: list, target: list) -> str:
    # 1. 프롬프트에 넣을 이전 대화 요약 (참고용)
    ref_text = "\n".join([f"{h['user_id']}: {h['content']}" for h in reference])

    # 2. 요약 대상 대화
    tgt_messages = "\n".join([f"{h['role']}: {h['content']}" for h in target])

    # 3. GPT 요청용 메시지 구성
    messages = [
        {"role": "system", "content": "너는 커플 상담 전문가야."},
        {"role": "user", "content": f"다음은 참고용 과거 대화야:\n{ref_text}"},
        {"role": "user", "content": f"다음은 최근 대화 내용이야 (요약용):\n{tgt_messages}"},
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