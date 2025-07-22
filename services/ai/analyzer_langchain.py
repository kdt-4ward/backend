from services.ai.prompt_templates import PROMPT_REGISTRY
from typing import List, Optional
from utils.langchain_helpers import run_langchain_prompt
from utils.log_utils import get_logger

logger = get_logger(__name__)

async def analyze_daily(messages: List[str],
                        emotions: Optional[List[str]] = None,
                        prompt_name: str = "daily_nlu",
                        user1_id: Optional[str] = None,
                        user2_id: Optional[str] = None) -> dict:
    
    logger.info(f"[analyze_daily][{prompt_name}] messages: {messages}")
    input_vars = {"messages": messages}
    
    if emotions is not None:
        logger.info(f"[analyze_daily][{prompt_name}] emotions: {emotions}")
        input_vars["emotions"] = emotions
    
    # 사용자 이름 매개변수 추가
    if user1_id:
        input_vars["user1_id"] = user1_id
    if user2_id:
        input_vars["user2_id"] = user2_id

    return await run_langchain_prompt(
        PROMPT_REGISTRY[prompt_name], 
        input_vars
    )

def aggregate_weekly_stats(daily_stats: list) -> dict:
    """ 일간 채팅 분석 결과 리스트를 항목별로 7일 시계열 리스트로 변환"""
    agg = {
        "user_stats": {},
        "summary": []
    }
    try:
        for day in daily_stats:
            day_result = day["result"]
            for user_id, values in day_result["user_stats"].items():
                if user_id not in agg["user_stats"]:
                    agg["user_stats"][user_id] = {
                        "affection": {"count": [], "samples": []},
                        "empathy": {"count": [], "samples": []},
                        "initiative": {"count": [], "samples": []},
                        "encouragement": {"count": [], "samples": []},
                        "conflict": {"count": [], "samples": []}
                    }
                agg["user_stats"][user_id]["affection"]["count"].append(int(values.get("affection", {}).get("count", 0)))
                agg["user_stats"][user_id]["affection"]["samples"].append(values.get("affection", {}).get("samples", []))
                agg["user_stats"][user_id]["empathy"]["count"].append(int(values.get("empathy", {}).get("count", 0)))
                agg["user_stats"][user_id]["empathy"]["samples"].append(values.get("empathy", {}).get("samples", []))
                agg["user_stats"][user_id]["initiative"]["count"].append(int(values.get("initiative", {}).get("count", 0)))
                agg["user_stats"][user_id]["initiative"]["samples"].append(values.get("initiative", {}).get("samples", []))
                agg["user_stats"][user_id]["encouragement"]["count"].append(int(values.get("encouragement", {}).get("count", 0)))
                agg["user_stats"][user_id]["encouragement"]["samples"].append(values.get("encouragement", {}).get("samples", []))
                agg["user_stats"][user_id]["conflict"]["count"].append(int(values.get("conflict", {}).get("count", 0)))
                agg["user_stats"][user_id]["conflict"]["samples"].append(values.get("conflict", {}).get("samples", []))
            agg["summary"].append(day_result.get("summary", ""))
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
        "emotion": [],
        "topic": [],
        "positive": {"count": [], "samples": []},
        "negative": {"count": [], "samples": []},
        "important_signal": [],
        "summary": []
    }
    try:
        for day in daily_ai_stats:
            agg["emotion"].append(day.get("emotion", []))
            agg["topic"].append(day.get("topic", []))
            agg["positive"]["count"].append(int(day.get("positive", {}).get("count", 0)))
            agg["positive"]["samples"].append(day.get("positive", {}).get("samples", []))
            agg["negative"]["count"].append(int(day.get("negative", {}).get("count", 0)))
            agg["negative"]["samples"].append(day.get("negative", {}).get("samples", []))
            agg["important_signal"].append(day.get("important_signal", ""))
            agg["summary"].append(day.get("summary", ""))
        return agg
    except Exception as e:
        logger.error(f"[aggregate_weekly_ai_stats_by_day] 집계 에러: {e} | daily_ai_stats={daily_ai_stats}")
        return {"error": "주간 AI 상담 통계 집계 에러", "detail": str(e)}