import json
from services.ai.prompt_templates import PROMPT_REGISTRY
from utils.langchain_helpers import run_langchain_prompt
from utils.log_utils import get_logger
from db.db_tables import UserTraitSummary

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
        """주간 분석 파이프라인 메인 함수"""
        
        # 1. 커플 주간 분석
        couple_result = await self._analyze_couple_weekly(couple_weekly, user1_id, user2_id)
        
        # 2. 개인 AI 주간 분석
        user1_result = await self._analyze_user_ai_weekly(user1_ai_weekly, user1_id)
        user2_result = await self._analyze_user_ai_weekly(user2_ai_weekly, user2_id)
        
        # 3. 커플 vs AI 비교 분석
        compare_result = await self._analyze_comparison(
            couple_weekly, user1_ai_weekly, user2_ai_weekly, user1_id, user2_id
        )
        
        # 4. 솔루션 생성
        solution = await self._generate_solution(
            couple_result, user1_result, user2_result, compare_result, user1_id, user2_id
        )
        
        # 5. 최종 솔루션 출력 생성
        solution_output = await self._generate_solution_output(
            couple_result, compare_result, user1_id, user2_id
        )
        
        # 6. 결과 조합
        couple_result["result"]["summary"] = solution_output['result']
        
        return {
            "주간커플분석": couple_result,
            "개인분석": {f"{user1_id}": user1_result, f"{user2_id}": user2_result},
            "커플vsAI차이": compare_result,
            "추천": solution
        }

    async def _analyze_couple_weekly(self, couple_weekly, user1_id, user2_id):
        """커플 주간 분석 수행"""
        result = await run_langchain_prompt(
            PROMPT_REGISTRY['couple_weekly_prompt'],
            {
                "user1_id": user1_id,
                "user2_id": user2_id,
                "couple_weekly": json.dumps(couple_weekly, ensure_ascii=False)
            },
            max_tokens=3000,
            log_prefix="couple_weekly_data"
        )
        self.log_failure(result, couple_weekly, "커플_주간분석")
        return result

    async def _analyze_user_ai_weekly(self, ai_weekly, user_id):
        """개인 AI 주간 분석 수행"""
        result = await run_langchain_prompt(
            PROMPT_REGISTRY['ai_weekly_prompt'],
            {
                "user_id": user_id,
                "ai_weekly": json.dumps(ai_weekly, ensure_ascii=False)
            },
            max_tokens=3000,
            log_prefix="ai_weekly"
        )
        self.log_failure(result, ai_weekly, "AI_주간분석")
        return result

    async def _analyze_comparison(self, couple_weekly, user1_ai_weekly, user2_ai_weekly, user1_id, user2_id):
        """커플 vs AI 비교 분석 수행"""
        result = await run_langchain_prompt(
            PROMPT_REGISTRY['compare_prompt'],
            {
                "user1_id": user1_id,
                "user2_id": user2_id,
                "couple_weekly": json.dumps(couple_weekly, ensure_ascii=False),
                "user1_ai_weekly": json.dumps(user1_ai_weekly, ensure_ascii=False),
                "user2_ai_weekly": json.dumps(user2_ai_weekly, ensure_ascii=False)
            },
            max_tokens=3000,
            log_prefix="couple_ai_compare"
        )
        self.log_failure(result, {
            "couple_weekly": json.dumps(couple_weekly, ensure_ascii=False),
            "user1_ai_weekly": json.dumps(user1_ai_weekly, ensure_ascii=False),
            "user2_ai_weekly": json.dumps(user2_ai_weekly, ensure_ascii=False)
        }, "비교분석")
        return result

    async def _generate_solution(self, couple_result, user1_result, user2_result, compare_result, user1_id, user2_id):
        """솔루션 생성"""
        result = await run_langchain_prompt(
            PROMPT_REGISTRY['solution_prompt'],
            {
                "user1_id": user1_id,
                "user2_id": user2_id,
                "couple_report": json.dumps(couple_result['result'], ensure_ascii=False) if couple_result['success'] else "",
                "user1_ai_report": json.dumps(user1_result['result'], ensure_ascii=False) if user1_result['success'] else "",
                "user2_ai_report": json.dumps(user2_result['result'], ensure_ascii=False) if user2_result['success'] else "",
                "compare_result": json.dumps(compare_result['result'], ensure_ascii=False) if compare_result['success'] else ""
            },
            max_tokens=3000,
            log_prefix="solution"
        )
        
        self.log_failure(result, {
            "couple_report": couple_result['result'] if couple_result['success'] else "",
            "user1_ai_report": user1_result['result'] if user1_result['success'] else "",
            "user2_ai_report": user2_result['result'] if user2_result['success'] else "",
            "compare_result": compare_result['result'] if compare_result['success'] else ""
        }, "solution")
        return result

    async def _generate_solution_output(self, couple_result, compare_result, user1_id, user2_id):
        """최종 솔루션 출력 생성"""
        # 사용자 성향 정보 조회
        user1_traits = self._get_user_traits(user1_id)
        user2_traits = self._get_user_traits(user2_id)
        
        result = await run_langchain_prompt(
            PROMPT_REGISTRY['solution_output_prompt'],
            {
                "user1_id": user1_id,
                "user2_id": user2_id,
                "user1_traits": user1_traits,
                "user2_traits": user2_traits,
                "summary": couple_result['result']['summary'],
                "compare_result": compare_result['result']
            },
            max_tokens=3000,
            log_prefix="solution_output"
        )
        
        self.log_failure(result, {
            "user1_traits": user1_traits,
            "user2_traits": user2_traits,
            "summary": couple_result['result']['summary'],
            "compare_result": compare_result['result']
        }, "solution_output")
        return result

    def _get_user_traits(self, user_id):
        """사용자 성향 정보 조회"""
        user_traits = self.db.query(UserTraitSummary).filter_by(user_id=user_id).first()
        return user_traits.summary if user_traits else "Not Given"