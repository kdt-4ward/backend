from services.ai.prompt_templates import PROMPT_REGISTRY
from typing import List
from utils.langchain_helpers import run_langchain_prompt
from utils.log_utils import get_logger

logger = get_logger(__name__)

async def analyze_daily(messages: List[str], emotions: List[str] = None, prompt_name: str = "daily_nlu") -> dict:
    
    logger.info(f"[analyze_daily][{prompt_name}] messages: {messages}")
    input_vars = {"messages": messages}
    
    if emotions is not None:
        logger.info(f"[analyze_daily][{prompt_name}] emotions: {emotions}")
        input_vars["emotions"] = emotions

    return await run_langchain_prompt(
        PROMPT_REGISTRY[prompt_name], 
        input_vars
    )

def aggregate_weekly_stats(daily_stats: list) -> dict:
    """ 일간 채팅 분석 결과 리스트를 항목별로 7일 시계열 리스트로 변환"""
    agg = {
        "user_stats": {
            "user_1":  {
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
            },
            "user_2":  {
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
            }
        },
        "요약리스트": []
    }
    try:
        for day in daily_stats:
            day_result = day["result"]
            for user_id, values in day_result["user_stats"].items():
                agg["user_stats"][user_id]["애정표현_횟수"].append(int(values.get("애정표현_횟수", 0)))
                agg["user_stats"][user_id]["애정표현_전체샘플"].append(values.get("애정표현_샘플", []))
                agg["user_stats"][user_id]["배려_횟수"].append(int(values.get("배려_횟수", 0)))
                agg["user_stats"][user_id]["배려_전체샘플"].append(values.get("배려_샘플", []))
                agg["user_stats"][user_id]["적극_횟수"].append(int(values.get("적극_횟수", 0)))
                agg["user_stats"][user_id]["적극_전체샘플"].append(values.get("적극_샘플", []))
                agg["user_stats"][user_id]["격려_횟수"].append(int(values.get("격려_횟수", 0)))
                agg["user_stats"][user_id]["격려_전체샘플"].append(values.get("격려_샘플", []))
                agg["user_stats"][user_id]["갈등_횟수"].append(int(values.get("갈등_횟수", 0)))
                agg["user_stats"][user_id]["갈등_전체샘플"].append(values.get("갈등_샘플", []))
            agg["요약리스트"].append(day_result.get("요약", ""))
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