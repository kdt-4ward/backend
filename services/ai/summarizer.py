from services.openai_client import call_openai_completion
from db.db import SessionLocal
from datetime import datetime
from utils.log_utils import get_logger

logger = get_logger(__name__)

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