from core.dependencies import get_langchain_llm
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from services.ai.prompt_templates import PROMPT_REGISTRY
from typing import List
import json
import logging
from utils.langchain_helpers import run_langchain_prompt

logger = logging.getLogger(__name__)

async def analyze_daily(messages: List[str], prompt_name: str) -> dict:
    text = "\n".join(messages)
    return await run_langchain_prompt(PROMPT_REGISTRY[prompt_name], {"messages": text})

def aggregate_weekly_stats(daily_stats: list) -> dict:
    """일간 통계 리스트를 주간 누적 통계로 합침 (부정/갈등 포함)"""
    agg = {
        "애정표현_총합": 0,
        "애정표현_전체샘플": [],
        "배려_총합": 0,
        "배려_전체샘플": [],
        "적극_총합": 0,
        "적극_전체샘플": [],
        "격려_총합": 0,
        "격려_전체샘플": [],
        "갈등_총합": 0,
        "갈등_전체샘플": [],
        "요약리스트": []
    }
    try:
        for day in daily_stats:
            agg["애정표현_총합"] += int(day.get("애정표현_횟수", 0))
            agg["애정표현_전체샘플"] += day.get("애정표현_샘플", [])
            agg["배려_총합"] += int(day.get("배려_횟수", 0))
            agg["배려_전체샘플"] += day.get("배려_샘플", [])
            agg["적극_총합"] += int(day.get("적극_횟수", 0))
            agg["적극_전체샘플"] += day.get("적극_샘플", [])
            agg["격려_총합"] += int(day.get("격려_횟수", 0))
            agg["격려_전체샘플"] += day.get("격려_샘플", [])
            agg["갈등_총합"] += int(day.get("갈등_횟수", 0))
            agg["갈등_전체샘플"] += day.get("갈등_샘플", [])
            agg["요약리스트"].append(day.get("요약", ""))
        # 샘플 중복 제거, 최대 5개로 제한 (필요 시)
        for k in [
            "애정표현_전체샘플", "배려_전체샘플",
            "적극_전체샘플", "격려_전체샘플",
            "갈등_전체샘플"
        ]:
            agg[k] = list({x for x in agg[k] if x})[:5]
        return agg
    except Exception as e:
        logger.error(f"[aggregate_weekly_stats] 집계 에러: {e} | daily_stats={daily_stats}")
        return {"error": "주간 통계 집계 에러", "detail": str(e)}

def aggregate_weekly_ai_stats(daily_ai_stats: list) -> dict:
    """일간 AI 상담 분석 결과 리스트를 주간 통합(트렌드/통계/샘플/요약 등)"""
    from collections import Counter

    try:
        emotion_counter = Counter()
        topic_counter = Counter()
        pos_count, neg_count = 0, 0
        pos_samples, neg_samples = [], []
        important_signals = []
        summary_list = []

        for day in daily_ai_stats:
            # 대표감정/상담주제는 리스트로 들어옴
            for emo in day.get("대표감정", []):
                if emo:
                    emotion_counter[emo] += 1
            for topic in day.get("상담주제", []):
                if topic:
                    topic_counter[topic] += 1

            pos_count += int(day.get("긍정발화_횟수", 0))
            neg_count += int(day.get("부정발화_횟수", 0))
            pos_samples += day.get("긍정발화_샘플", [])
            neg_samples += day.get("부정발화_샘플", [])

            signal = day.get("중요신호")
            if signal:
                important_signals.append(signal)
            summary_list.append(day.get("요약", ""))

        # 대표감정/주제는 가장 많이 등장한 순서대로 2개씩만
        weekly_emotions = [x for x, _ in emotion_counter.most_common(2)]
        weekly_topics = [x for x, _ in topic_counter.most_common(2)]
        # 샘플 문장은 중복 제거, 최대 5개
        pos_samples = list({s for s in pos_samples if s})[:5]
        neg_samples = list({s for s in neg_samples if s})[:5]
        important_signals = [s for s in important_signals if s][:5]

        return {
            "대표감정": weekly_emotions,
            "상담주제": weekly_topics,
            "긍정발화_총합": pos_count,
            "긍정발화_전체샘플": pos_samples,
            "부정발화_총합": neg_count,
            "부정발화_전체샘플": neg_samples,
            "주요신호리스트": important_signals,
            "요약리스트": summary_list
        }
    except Exception as e:
        logger.error(f"[aggregate_weekly_ai_stats] 집계 에러: {e} | daily_ai_stats={daily_ai_stats}")
        return {"error": "주간 AI 상담 통계 집계 에러", "detail": str(e)}
