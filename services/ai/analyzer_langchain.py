from core.dependencies import get_langchain_llm
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from services.ai.prompt_templates import DAILY_NLU_PROMPT, WEEKLY_REPORT_PROMPT
import json

llm = get_langchain_llm()

daily_chain = ChatPromptTemplate.from_template(DAILY_NLU_PROMPT) | llm | StrOutputParser()

async def summarize_and_count_by_day(messages: list[str]) -> dict:
    text = "\n".join(messages)
    if len(text) > 2000:
        text = text[:2000] + "\n(이하 생략)"
    result = await daily_chain.ainvoke({"messages": text})
    import json
    try:
        parsed = json.loads(result)
    except Exception:
        parsed = {"llm_raw_result": result}
    return parsed

weekly_chain = ChatPromptTemplate.from_template(WEEKLY_REPORT_PROMPT) | llm | StrOutputParser()


def aggregate_weekly_stats(daily_stats: list) -> dict:
    """일간 통계 리스트를 주간 누적 통계로 합침"""
    agg = {
        "애정표현_총합": 0,
        "애정표현_전체샘플": [],
        "배려_총합": 0,
        "배려_전체샘플": [],
        "적극_총합": 0,
        "적극_전체샘플": [],
        "격려_총합": 0,
        "격려_전체샘플": [],
        "요약리스트": []
    }
    for day in daily_stats:
        agg["애정표현_총합"] += int(day.get("애정표현_횟수", 0))
        agg["애정표현_전체샘플"] += day.get("애정표현_샘플", [])
        agg["배려_총합"] += int(day.get("배려_횟수", 0))
        agg["배려_전체샘플"] += day.get("배려_샘플", [])
        agg["적극_총합"] += int(day.get("적극_횟수", 0))
        agg["적극_전체샘플"] += day.get("적극_샘플", [])
        agg["격려_총합"] += int(day.get("격려_횟수", 0))
        agg["격려_전체샘플"] += day.get("격려_샘플", [])
        agg["요약리스트"].append(day.get("요약", ""))
    # 샘플 중복 제거, 최대 5개로 제한 (필요 시)
    for k in ["애정표현_전체샘플", "배려_전체샘플", "적극_전체샘플", "격려_전체샘플"]:
        agg[k] = list({x for x in agg[k] if x})[:5]
    return agg

async def generate_weekly_solution_with_llm(daily_stats: list) -> dict:
    """
    daily_stats: 하루별 LLM 통계/요약 리스트
    """
    # daily_stats를 주간 통계로 변환
    weekly_stats = aggregate_weekly_stats(daily_stats)
    weekly_input = json.dumps(weekly_stats, ensure_ascii=False, indent=2)

    result = await weekly_chain.ainvoke({"weekly_stats": weekly_input})
    try:
        parsed = json.loads(result)
    except Exception:
        parsed = {"llm_raw_result": result}
    return parsed