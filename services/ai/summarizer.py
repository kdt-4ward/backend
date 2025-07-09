from services.openai_client import call_openai_completion
from models.db_models import AIChatSummary, CoupleChatSummary
from db.db import SessionLocal
from datetime import datetime

async def summarize_ai_chat(prev_summary: str, target: list) -> str:
    """
    누적 요약 방식: 이전 summary(요약) + 최근 미요약 메시지(target)만 받아
    전체 누적 요약을 새로 만듭니다.
    """

    # 이전 누적 요약이 없을 때는 빈 문자열 처리
    prev_summary_text = prev_summary if prev_summary else "(없음)"
    target_text = "\n".join([f"{h['role']}: {h['content']}" for h in target])

    prompt = f"""
지금까지의 누적 요약:
{prev_summary_text}

아직 요약되지 않은 최근 대화들:
{target_text}

이 내용을 종합해서, 최신까지의 전체 누적 요약을 다시 작성해 주세요.
"""

    messages = [
        {"role": "system", "content": "너는 사용자와 대화를 지속적으로 하기 위해 누적요약을 해주는 시스템이야. 대화의 맥락을 유지하기 위해 누적 요약본을 보고 최근 대화를 요약해줘."},
        {"role": "user", "content": prompt.strip()}
    ]

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