import json
from services.ai.prompt_templates import PROMPT_REGISTRY
from utils.langchain_helpers import run_langchain_prompt
from utils.log_utils import get_logger
from db.crud import get_user_name, get_users_by_couple_id

logger = get_logger(__name__)


class WeeklyAnalysisPipeline:
    def __init__(self, db_session):
        self.db = db_session
    
    def log_failure(self, result, input_data, mode):
        if not result['success']:
            raw = result.get('raw', '')
            logger.warning(f"[WeeklyAnalysis] {mode} 실패: {result.get('error')} | 입력={self.short_input(input_data)} | LLM응답 일부={self.short_input(raw)}")
    
    @staticmethod
    def short_input(data, limit=500):
        try:
            s = json.dumps(data, ensure_ascii=False)
        except Exception:
            s = str(data)
        return s if len(s) < limit else s[:limit] + " ...[이하 생략]"

    async def analyze(self, couple_weekly, user1_ai_weekly, user2_ai_weekly, couple_id, user1_id, user2_id):
        # 사용자 이름 가져오기
        user1_name = get_user_name(self.db, user1_id)
        user2_name = get_user_name(self.db, user2_id)

        couple_result = await run_langchain_prompt(
            PROMPT_REGISTRY['couple_weekly_prompt'],
            {
                "user1_id": user1_id,
                "user2_id": user2_id,
                "user1_name": user1_name,
                "user2_name": user2_name,
                "couple_weekly": json.dumps(couple_weekly, ensure_ascii=False)
            },
            expected_json_key="커플_주간분석",
            max_tokens=3000,
            log_prefix="couple_weekly_data"
        )
        self.log_failure(couple_result, couple_weekly, "커플_주간분석")

        user1_result = await run_langchain_prompt(
            PROMPT_REGISTRY['ai_weekly_prompt'],
            {
                "user_name": user1_name,
                "ai_weekly": json.dumps(user1_ai_weekly, ensure_ascii=False)
            },
            expected_json_key="AI_주간분석",
            max_tokens=3000,
            log_prefix="ai_weekly"
        )
        self.log_failure(user1_result, user1_ai_weekly, "AI_주간분석")

        user2_result = await run_langchain_prompt(
            PROMPT_REGISTRY['ai_weekly_prompt'],
            {
                "user_name": user2_name,
                "ai_weekly": json.dumps(user2_ai_weekly, ensure_ascii=False)
            },
            expected_json_key="AI_주간분석",
            max_tokens=3000,
            log_prefix="ai_weekly"
        )
        self.log_failure(user2_result, user2_ai_weekly, "AI_주간분석")

        compare_result = await run_langchain_prompt(
            PROMPT_REGISTRY['compare_prompt'],
            {
                "user1_name": user1_name,
                "user2_name": user2_name,
                "couple_weekly": json.dumps(couple_weekly, ensure_ascii=False),
                "user1_ai_weekly": json.dumps(user1_ai_weekly, ensure_ascii=False),
                "user2_ai_weekly": json.dumps(user2_ai_weekly, ensure_ascii=False)
            },
            expected_json_key="비교분석",
            max_tokens=3000,
            log_prefix="couple_ai_compare"
        )
        self.log_failure(compare_result, {
                "couple_weekly": json.dumps(couple_weekly, ensure_ascii=False),
                "user1_ai_weekly": json.dumps(user1_ai_weekly, ensure_ascii=False),
                "user2_ai_weekly": json.dumps(user2_ai_weekly, ensure_ascii=False)
            }, "비교분석")

        solution = await run_langchain_prompt(
            PROMPT_REGISTRY['solution_prompt'],
            {
                "user1_name": user1_name,
                "user2_name": user2_name,
                "couple_report": json.dumps(couple_result['result'], ensure_ascii=False) if couple_result['success'] else "",
                "user1_ai_report": json.dumps(user1_result['result'], ensure_ascii=False) if user1_result['success'] else "",
                "user2_ai_report": json.dumps(user2_result['result'], ensure_ascii=False) if user2_result['success'] else "",
                "compare_result": json.dumps(compare_result['result'], ensure_ascii=False) if compare_result['success'] else ""
            },
            max_tokens=3000,
            log_prefix="solution"
        )

        self.log_failure(solution, {
                "couple_report": couple_result['result'] if couple_result['success'] else "",
                "user1_ai_report": user1_result['result'] if user1_result['success'] else "",
                "user2_ai_report": user2_result['result'] if user2_result['success'] else "",
                "compare_result": compare_result['result'] if compare_result['success'] else ""
            }, "solution")

        return {
            "주간커플분석": couple_result,
            "개인분석": {"{user1_id}": user1_result, "{user2_id}": user2_result},
            "커플vsAI차이": compare_result,
            "추천": solution
        }