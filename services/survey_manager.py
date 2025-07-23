from sqlalchemy.orm import Session
from db.db_tables import SurveyQuestion, SurveyChoice, UserSurveyResponse, Couple
from typing import List, Optional, Dict, Any
from datetime import datetime
import random
import json
import asyncio
from utils.log_utils import get_logger
from services.openai_client import call_openai_completion
from services.ai.user_personality_summary import summarize_personality_from_tags
from db.crud import get_user_traits, save_user_trait_summary
from core.redis_v2.persona_config_service import PersonaConfigService
from core.redis_v2.redis import redis_client

logger = get_logger(__name__)

class SurveyManager:
    def __init__(self, db: Session):
        self.db = db
    
    def get_unanswered_questions(self, user_id: str) -> List[Dict[str, Any]]:
        """
        사용자가 아직 답변하지 않은 성향 질문들을 조회합니다.
        """
        try:
            # LEFT JOIN을 사용하여 답변하지 않은 질문만 한 번에 조회
            unanswered_questions = (
                self.db.query(SurveyQuestion, SurveyChoice)
                .outerjoin(
                    UserSurveyResponse,
                    (SurveyQuestion.id == UserSurveyResponse.question_id) & 
                    (UserSurveyResponse.user_id == user_id)
                )
                .join(SurveyChoice, SurveyQuestion.id == SurveyChoice.question_id)  # 질문과 선택지 JOIN 추가
                .filter(UserSurveyResponse.question_id.is_(None))
                .order_by(SurveyQuestion.order)
                .all()
            )
            
            # 결과를 질문별로 그룹화
            question_map = {}
            for question, choice in unanswered_questions:
                if question.id not in question_map:
                    question_map[question.id] = {
                        "question_id": question.id,
                        "code": question.code,
                        "text": question.text,
                        "order": question.order,
                        "choices": []
                    }
                
                if choice:  # choice가 None이 아닌 경우만 추가
                    question_map[question.id]["choices"].append({
                        "choice_id": choice.id,
                        "text": choice.text,
                        "tag": choice.tag
                    })
            
            result = list(question_map.values())
            logger.info(f"[SurveyManager] 사용자 {user_id}의 미답변 질문 수: {len(result)}")
            return result
            
        except Exception as e:
            logger.error(f"[SurveyManager] 미답변 질문 조회 실패: {e}")
            return []
    
    async def select_contextual_question(self, user_id: str, conversation_context: str = "") -> Optional[Dict[str, Any]]:
        """
        OpenAI를 활용하여 현재 대화 맥락에 맞는 성향 질문을 선택합니다.
        """
        try:
            unanswered_questions = self.get_unanswered_questions(user_id)
            
            if not unanswered_questions:
                logger.info(f"[SurveyManager] 사용자 {user_id}의 모든 성향 질문이 완료되었습니다.")
                return None
            
            # 대화 맥락이 없는 경우 기본 로직 사용
            if not conversation_context.strip():
                return
            
            # OpenAI를 활용한 맥락적 질문 선택
            selected_question = await self._select_question_with_ai(unanswered_questions, conversation_context)
            
            if selected_question:
                logger.info(f"[SurveyManager] AI 선택된 질문: {selected_question['text']}")
                return selected_question
            
            # AI 선택이 실패한 경우 기본 로직으로 fallback
            logger.warning(f"[SurveyManager] AI 질문 선택 실패, 기본 로직으로 fallback")
            return self._select_question_by_priority(unanswered_questions)
            
        except Exception as e:
            logger.error(f"[SurveyManager] 맥락적 질문 선택 실패: {e}")
            # 에러 발생 시 기본 로직으로 fallback
            return self._select_question_by_priority(unanswered_questions)
    
    def _select_question_by_priority(self, unanswered_questions: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        우선순위 기반 질문 선택 (기본 로직)
        """
        # order별로 그룹화
        question_groups = {}
        for question in unanswered_questions:
            order = question["order"]
            if order not in question_groups:
                question_groups[order] = []
            question_groups[order].append(question)
        
        # 가장 낮은 order부터 선택
        for order in sorted(question_groups.keys()):
            questions_in_order = question_groups[order]
            if questions_in_order:
                # 같은 order 내에서 랜덤 선택
                selected_question = random.choice(questions_in_order)
                logger.info(f"[SurveyManager] 우선순위 선택된 질문: {selected_question['text']}")
                return selected_question
        
        return None
    
    async def _select_question_with_ai(self, unanswered_questions: List[Dict[str, Any]], conversation_context: str) -> Optional[Dict[str, Any]]:
        """
        OpenAI를 활용하여 대화 맥락에 맞는 질문을 선택합니다.
        """
        try:
            # 질문 목록을 JSON 형태로 준비
            questions_json = []
            for q in unanswered_questions:
                question_data = {
                    "question_id": q["question_id"],
                    "text": q["text"],
                    "code": q["code"],
                    "choices": [choice["text"] for choice in q["choices"]]
                }
                questions_json.append(question_data)
            
            # OpenAI 프롬프트 구성
            prompt = f"""
당신은 연애 상담 AI 챗봇입니다. 사용자와의 대화 맥락을 고려하여 가장 적절한 성향 질문을 선택해야 합니다.

[현재 대화 맥락]
{conversation_context}

[사용 가능한 성향 질문들]
{json.dumps(questions_json, ensure_ascii=False, indent=2)}

위 질문들 중에서 현재 대화 맥락과 가장 관련성이 높고, 사용자에게 자연스럽게 물어볼 수 있는 질문을 하나 선택해주세요.

선택 기준:
1. 현재 대화 주제와 직접적으로 관련된 질문
2. 사용자의 상황을 더 잘 이해하는데 도움이 되는 질문
3. 자연스럽게 대화 흐름에 삽입할 수 있는 질문

JSON 형식으로 응답해주세요:
{{
    "selected_question_id": 선택한_질문의_ID,
    "reasoning": "선택 이유 (간단히 설명)"
}}

선택할 수 없는 경우 null을 반환하세요.
"""
            
            # OpenAI 호출
            response = await call_openai_completion([{"role": "user", "content": prompt}])
            
            # 응답 파싱
            try:
                result = json.loads(response)
                selected_id = result.get("selected_question_id")
                reasoning = result.get("reasoning", "")
                
                if selected_id:
                    # 선택된 질문 찾기
                    for question in unanswered_questions:
                        if question["question_id"] == selected_id:
                            logger.info(f"[SurveyManager] AI 선택 이유: {reasoning}")
                            return question
                    
                    logger.warning(f"[SurveyManager] AI가 선택한 질문 ID {selected_id}를 찾을 수 없음")
                    return None
                else:
                    logger.info(f"[SurveyManager] AI가 적절한 질문을 찾지 못함")
                    return None
                    
            except json.JSONDecodeError as e:
                logger.error(f"[SurveyManager] AI 응답 JSON 파싱 실패: {e}, 응답: {response}")
                return None
                
        except Exception as e:
            logger.error(f"[SurveyManager] AI 질문 선택 중 오류: {e}")
            return None
    
    def save_survey_response(self, user_id: str, question_id: int, choice_id: Optional[int] = None, custom_input: Optional[str] = None) -> bool:
        """
        사용자의 성향 질문 답변을 저장합니다.
        """
        try:
            # 기존 응답이 있는지 확인
            existing_response = self.db.query(UserSurveyResponse).filter(
                UserSurveyResponse.user_id == user_id,
                UserSurveyResponse.question_id == question_id
            ).first()
            
            if existing_response:
                logger.warning(f"[SurveyManager] 사용자 {user_id}의 질문 {question_id}에 대한 응답이 이미 존재합니다.")
                return False
            
            # 새로운 응답 저장
            response = UserSurveyResponse(
                user_id=user_id,
                question_id=question_id,
                choice_id=choice_id,
                custom_input=custom_input,
                submitted_at=datetime.utcnow()
            )
            
            self.db.add(response)
            self.db.commit()
            self.db.refresh(response)
            
            logger.info(f"[SurveyManager] 성향 질문 응답 저장 완료: user_id={user_id}, question_id={question_id}")
            
            # 백그라운드에서 성향 분석 실행 (세션 정보 전달)
            asyncio.create_task(self._update_personality_analysis(user_id, self.db))
            
            return True
            
        except Exception as e:
            logger.error(f"[SurveyManager] 성향 질문 응답 저장 실패: {e}")
            self.db.rollback()
            return False
    
    async def _update_personality_analysis(self, user_id: str, db_session):
        """
        백그라운드에서 성향 분석을 실행하고 Redis 캐시를 업데이트합니다.
        """
        try:
            logger.info(f"[SurveyManager] 성향 분석 시작: user_id={user_id}")
            
            # 전달받은 세션 사용
            # 사용자의 모든 성향 응답 조회
            responses = get_user_traits(db_session, user_id)
            
            if not responses:
                logger.warning(f"[SurveyManager] 사용자 {user_id}의 성향 응답이 없습니다.")
                return
            
            # 사용자 이름 조회
            from db.db_tables import User
            user = db_session.query(User).filter_by(user_id=user_id).first()
            user_name = user.name if user else "사용자"
            
            # AI를 활용한 성향 분석
            summary = await summarize_personality_from_tags(responses, user_name=user_name)
            
            # 데이터베이스에 성향 요약 저장
            save_user_trait_summary(db_session, user_id, summary)
            
            # Redis 캐시 업데이트
            await self._update_redis_cache(user_id, summary, db_session)
            
            logger.info(f"[SurveyManager] 성향 분석 완료: user_id={user_id}")
                
        except Exception as e:
            logger.error(f"[SurveyManager] 성향 분석 실패: user_id={user_id}, error={e}")
    
    async def _update_redis_cache(self, user_id: str, new_summary: str, db_session):
        """
        Redis에 저장된 사용자 성향 정보를 업데이트하고 system prompt를 새로고침합니다.
        """
        try:
            # 커플 ID 조회 (전달받은 세션 사용)
            from db.db_tables import User
            user = db_session.query(User).filter_by(user_id=user_id).first()
            if not user or not user.couple_id:
                logger.warning(f"[SurveyManager] 사용자 {user_id}의 커플 정보를 찾을 수 없습니다.")
                return
            
            couple_id = user.couple_id
            
            # 1. PersonaConfigService 캐시 무효화
            config_service = PersonaConfigService(user_id, couple_id)
            config_service.invalidate_cache()
            
            # 2. 기존 Redis 클라이언트 사용하여 캐시 삭제
            cache_key = f"chat_config:{user_id}"
            redis_client.delete(cache_key)
            
            # 3. 대화 히스토리 캐시도 무효화하여 다음 요청 시 새로운 system prompt 로드
            from core.redis_v2.redis import RedisAIHistory
            history_redis = RedisAIHistory()
            history_redis.clear(user_id)
            
            logger.info(f"[SurveyManager] Redis 캐시 및 system prompt 업데이트 완료: user_id={user_id}")
                
        except Exception as e:
            logger.error(f"[SurveyManager] Redis 캐시 업데이트 실패: user_id={user_id}, error={e}")
    
    def format_question_for_chat(self, question: Dict[str, Any]) -> str:
        """
        AI 챗봇에서 자연스럽게 질문할 수 있도록 질문을 포맷팅합니다.
        """
        question_text = question["text"]
        choices = question["choices"]
        
        # 선택지가 있는 경우
        if choices:
            formatted_choices = []
            for i, choice in enumerate(choices, 1):
                formatted_choices.append(f"{i}. {choice['text']}")
            
            choices_text = "\n".join(formatted_choices)
            return f"{question_text}\n\n{choices_text}"
        
        # 주관식인 경우
        return f"{question_text}\n\n자유롭게 답변해주세요."
    
    async def parse_user_response_with_ai(self, question: Dict[str, Any], user_response: str) -> Dict[str, Any]:
        """
        OpenAI를 활용하여 사용자의 텍스트 응답을 정확하게 파싱합니다.
        """
        try:
            choices = question["choices"]
            
            # 선택지가 없는 주관식 질문인 경우
            if not choices:
                return {
                    "choice_id": None,
                    "custom_input": user_response
                }
            
            # 질문과 선택지 정보를 JSON 형태로 준비
            choices_json = []
            for i, choice in enumerate(choices, 1):
                choice_data = {
                    "choice_id": choice["choice_id"],
                    "number": i,
                    "text": choice["text"],
                    "tag": choice["tag"]
                }
                choices_json.append(choice_data)
            
            # OpenAI 프롬프트 구성
            prompt = f"""
당신은 사용자의 답변을 분석하여 적절한 선택지를 매칭하거나 자유 답변으로 분류하는 역할을 합니다.

[질문]
{question['text']}

[선택지]
{json.dumps(choices_json, ensure_ascii=False, indent=2)}

[사용자 답변]
"{user_response}"

위 사용자 답변을 분석하여 다음 중 하나로 분류해주세요:

1. 선택지 중 하나와 정확히 매칭되는 경우: 해당 choice_id 반환
2. 선택지와 유사하지만 완전히 일치하지 않는 경우: custom_input으로 분류
3. 선택지와 전혀 관련없는 자유 답변인 경우: custom_input으로 분류

분석 기준:
- 숫자로 답변한 경우 (1, 2, 3...): 해당 번호의 선택지 매칭
- 선택지 텍스트와 정확히 일치하거나 매우 유사한 경우: 해당 선택지 매칭
- 선택지와 관련은 있지만 다른 표현을 사용한 경우: custom_input으로 분류
- 완전히 다른 내용의 자유 답변인 경우: custom_input으로 분류

JSON 형식으로 응답해주세요:
{{
    "choice_id": 매칭된_선택지_ID_또는_null,
    "custom_input": 자유_답변_또는_null,
    "reasoning": "분류 이유 (간단히 설명)"
}}

예시:
- 사용자: "1번" → {{"choice_id": 1, "custom_input": null, "reasoning": "숫자 1로 첫 번째 선택지 선택"}}
- 사용자: "즉시 대화로 해결하려고 함" → {{"choice_id": 1, "custom_input": null, "reasoning": "첫 번째 선택지 텍스트와 정확히 일치"}}
- 사용자: "바로 말씀드려요" → {{"choice_id": null, "custom_input": "바로 말씀드려요", "reasoning": "첫 번째 선택지와 유사하지만 다른 표현"}}
- 사용자: "상황에 따라 다르게 해요" → {{"choice_id": null, "custom_input": "상황에 따라 다르게 해요", "reasoning": "선택지와 다른 자유 답변"}}
"""
            
            # OpenAI 호출
            response = await call_openai_completion([{"role": "user", "content": prompt}])
            
            # 응답 파싱
            try:
                result = json.loads(response)
                choice_id = result.get("choice_id")
                custom_input = result.get("custom_input")
                reasoning = result.get("reasoning", "")
                
                # choice_id가 숫자인 경우 실제 choice_id로 변환
                if choice_id is not None and isinstance(choice_id, int):
                    if 1 <= choice_id <= len(choices):
                        actual_choice_id = choices[choice_id - 1]["choice_id"]
                        logger.info(f"[SurveyManager] AI 파싱 결과: choice_id={actual_choice_id}, 이유: {reasoning}")
                        return {
                            "choice_id": actual_choice_id,
                            "custom_input": None
                        }
                    else:
                        logger.warning(f"[SurveyManager] AI가 선택한 번호 {choice_id}가 유효하지 않음")
                
                # custom_input이 있는 경우
                if custom_input:
                    logger.info(f"[SurveyManager] AI 파싱 결과: custom_input, 이유: {reasoning}")
                    return {
                        "choice_id": None,
                        "custom_input": custom_input
                    }
                
                # 기본값: custom_input으로 처리
                logger.info(f"[SurveyManager] AI 파싱 실패, 기본값 사용")
                return {
                    "choice_id": None,
                    "custom_input": user_response
                }
                    
            except json.JSONDecodeError as e:
                logger.error(f"[SurveyManager] AI 응답 JSON 파싱 실패: {e}, 응답: {response}")
                # JSON 파싱 실패 시 기본 로직 사용
                return self._parse_user_response_fallback(question, user_response)
                
        except Exception as e:
            logger.error(f"[SurveyManager] AI 답변 파싱 중 오류: {e}")
            # 에러 발생 시 기본 로직 사용
            return self._parse_user_response_fallback(question, user_response)
    
    def _parse_user_response_fallback(self, question: Dict[str, Any], user_response: str) -> Dict[str, Any]:
        """
        기본 답변 파싱 로직 (fallback용)
        """
        choices = question["choices"]
        
        # 선택지가 있는 경우, 숫자나 선택지 텍스트로 답변했는지 확인
        if choices:
            # 숫자로 답변한 경우 (1, 2, 3...)
            try:
                choice_number = int(user_response.strip())
                if 1 <= choice_number <= len(choices):
                    selected_choice = choices[choice_number - 1]
                    return {
                        "choice_id": selected_choice["choice_id"],
                        "custom_input": None
                    }
            except ValueError:
                pass
            
            # 선택지 텍스트로 답변한 경우
            for choice in choices:
                if choice["text"].lower() in user_response.lower():
                    return {
                        "choice_id": choice["choice_id"],
                        "custom_input": None
                    }
            
            # 매칭되지 않으면 custom_input으로 처리
            return {
                "choice_id": None,
                "custom_input": user_response
            }
        
        # 주관식인 경우
        return {
            "choice_id": None,
            "custom_input": user_response
        }
    
    def parse_user_response(self, question: Dict[str, Any], user_response: str) -> Dict[str, Any]:
        """
        사용자의 텍스트 응답을 파싱하여 choice_id와 custom_input을 추출합니다.
        (기존 함수 - 하위 호환성을 위해 유지)
        """
        return self._parse_user_response_fallback(question, user_response) 