from services.ai.prompt_templates import PROMPT_REGISTRY
from typing import List
import logging
from utils.langchain_helpers import run_langchain_prompt

logger = logging.getLogger(__name__)

async def analyze_daily(messages: List[str], prompt_name: str) -> dict:
    text = "\n".join(messages)
    return await run_langchain_prompt(PROMPT_REGISTRY[prompt_name], {"messages": text})

def aggregate_weekly_stats(daily_stats: list) -> dict:
    """ 일간 채팅 분석 결과 리스트를 항목별로 7일 시계열 리스트로 변환"""
    agg = {
        "애정표현_횟수": [],
        "애정표현_전체샘플": [],
        "배려_횟수": [],
        "배려_전체샘플": [],
        "적극_횟수": [],
        "적극_전체샘플": [],
        "격려_횟수": [],
        "격려_전체샘플": [],
        "갈등_횟수": [],
        "갈등_전체샘플": [],
        "요약리스트": []
    }
    try:
        for day in daily_stats:
            agg["애정표현_횟수"].append(int(day.get("애정표현_횟수", 0)))
            agg["애정표현_전체샘플"].append(day.get("애정표현_샘플", []))
            agg["배려_횟수"].append(int(day.get("배려_횟수", 0)))
            agg["배려_전체샘플"].append(day.get("배려_샘플", []))
            agg["적극_횟수"].append(int(day.get("적극_횟수", 0)))
            agg["적극_전체샘플"].append(day.get("적극_샘플", []))
            agg["격려_횟수"].append(int(day.get("격려_횟수", 0)))
            agg["격려_전체샘플"].append(day.get("격려_샘플", []))
            agg["갈등_횟수"].append(int(day.get("갈등_횟수", 0)))
            agg["갈등_전체샘플"].append(day.get("갈등_샘플", []))
            agg["요약리스트"].append(day.get("요약", ""))
        return agg
    except Exception as e:
        logger.error(f"[aggregate_weekly_stats] 집계 에러: {e} | daily_stats={daily_stats}")
        return {"error": "주간 통계 집계 에러", "detail": str(e)}

def aggregate_weekly_ai_stats_by_day(daily_ai_stats: list) -> dict:
    """
    일간 AI 상담 분석 결과 리스트를 항목별로 7일 시계열 리스트로 변환
    - 각 항목별로 7일치 값(혹은 리스트)이 들어감
    - 예: "대표감정": [["불안", "외로움"], ["희망"], ...], "긍정발화_횟수": [2, 1, ...]
    """
    agg = {
        "대표감정": [],
        "상담주제": [],
        "긍정발화_횟수": [],
        "긍정발화_샘플": [],
        "부정발화_횟수": [],
        "부정발화_샘플": [],
        "중요신호": [],
        "요약리스트": []
    }
    try:
        for day in daily_ai_stats:
            agg["대표감정"].append(day.get("대표감정", []))
            agg["상담주제"].append(day.get("상담주제", []))
            agg["긍정발화_횟수"].append(int(day.get("긍정발화_횟수", 0)))
            agg["긍정발화_샘플"].append(day.get("긍정발화_샘플", []))
            agg["부정발화_횟수"].append(int(day.get("부정발화_횟수", 0)))
            agg["부정발화_샘플"].append(day.get("부정발화_샘플", []))
            agg["중요신호"].append(day.get("중요신호", ""))
            agg["요약리스트"].append(day.get("요약", ""))
        return agg
    except Exception as e:
        logger.error(f"[aggregate_weekly_ai_stats_by_day] 집계 에러: {e} | daily_ai_stats={daily_ai_stats}")
        return {"error": "주간 AI 상담 통계 집계 에러", "detail": str(e)}