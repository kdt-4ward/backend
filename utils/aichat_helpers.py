from services.rag_search import search_past_chats
from services.survey_manager import SurveyManager
from db.db import SessionLocal
from sqlalchemy.orm import Session

def build_functions():
    return [
                {
                    "name": "search_past_chats",
                    "description": (
                        "질문과 관련된 실제 과거 대화 내용(채팅 메시지)을 검색하여, "
                        "정확한 근거가 필요하거나, 이전의 구체적인 사건, 날짜, 표현 등을 사용자가 물었을 때 반드시 사용해야 합니다. "
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": (
                                    "검색하고 싶은 키워드, 질문, 또는 자연어 문장. "
                                    "예: '작년 여름 여행', '우리가 마지막으로 싸운 이유', '상대방이 서운했던 순간'"
                                )
                            },
                            "top_k": {
                                "type": "integer",
                                "default": 3,
                                "description": (
                                    "관련성이 높은 결과(대화 chunk) 최대 개수. 필요시 늘릴 수 있음."
                                )
                            }
                        },
                        "required": ["query"]
                    }
                },
                {
                    "name": "get_survey_question",
                    "description": (
                        "사용자가 아직 답변하지 않은 성향 질문을 가져와서 대화 중에 자연스럽게 질문할 수 있도록 합니다. "
                        "사용자가 솔루션을 요청하거나 조언을 구할 때, 더 정확한 도움을 주기 위해 성향을 파악하는 질문을 할 수 있습니다."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "context": {
                                "type": "string",
                                "description": "적절한 질문을 위한 대화 맥락"
                            }
                        },
                        "required": ["context"]
                    }
                },
                {
                    "name": "save_survey_response",
                    "description": (
                        "사용자가 성향 질문에 답변한 내용을 저장합니다. "
                        "이 함수는 사용자가 성향 질문에 답변을 완료했을 때 호출되어야 합니다."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "question_id": {
                                "type": "integer",
                                "description": "답변한 질문의 ID"
                            },
                            "user_response": {
                                "type": "string",
                                "description": "사용자의 답변 텍스트 (선택지 번호, 선택지 텍스트, 또는 자유 답변)"
                            }
                        },
                        "required": ["question_id", "user_response"]
                    }
                }
            ]

def build_function_map(user_id: str, couple_id: str):
    return {
        "search_past_chats": lambda query, top_k=3: search_past_chats(
            query=query,
            top_k=top_k,
            user_id=user_id,
            couple_id=couple_id
        ),
        "get_survey_question": lambda context: get_survey_question(
            user_id=user_id,
            context=context
        ),
        "save_survey_response": lambda question_id, user_response: save_survey_response(
            user_id=user_id,
            question_id=question_id,
            user_response=user_response
        )
    }

async def get_survey_question(user_id: str, context: str) -> dict:
    """
    사용자에게 적절한 성향 질문을 제공합니다.
    """
    try:
        db = SessionLocal()
        survey_manager = SurveyManager(db)
        
        # 맥락에 맞는 질문 선택
        question = await survey_manager.select_contextual_question(user_id, context)
        
        if not question:
            return {
                "success": False,
                "message": "적절한 질문을 찾지 못했습니다.",
                "question": None
            }
        
        # 챗봇에서 자연스럽게 질문할 수 있도록 포맷팅
        formatted_question = survey_manager.format_question_for_chat(question)
        
        return {
            "success": True,
            "message": "성향 질문을 제공합니다.",
            "question": {
                "id": question["question_id"],
                "text": formatted_question,
                "original_text": question["text"],
                "choices": question["choices"]
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"성향 질문 조회 중 오류가 발생했습니다: {str(e)}",
            "question": None
        }
    finally:
        db.close()

async def save_survey_response(user_id: str, question_id: int, user_response: str) -> dict:
    """
    사용자의 성향 질문 답변을 저장합니다.
    """
    try:
        db = SessionLocal()
        survey_manager = SurveyManager(db)
        
        # 질문 정보 조회
        question_data = survey_manager.get_unanswered_questions(user_id)
        target_question = None
        
        for q in question_data:
            if q["question_id"] == question_id:
                target_question = q
                break
        
        if not target_question:
            return {
                "success": False,
                "message": "해당 질문을 찾을 수 없습니다."
            }
        
        # AI를 활용한 사용자 응답 파싱
        parsed_response = await survey_manager.parse_user_response_with_ai(target_question, user_response)
        
        # 응답 저장
        success = survey_manager.save_survey_response(
            user_id=user_id,
            question_id=question_id,
            choice_id=parsed_response["choice_id"],
            custom_input=parsed_response["custom_input"]
        )
        
        if success:
            return {
                "success": True,
                "message": "성향 질문 답변이 저장되었습니다.",
                "parsed_response": parsed_response
            }
        else:
            return {
                "success": False,
                "message": "답변 저장에 실패했습니다."
            }
            
    except Exception as e:
        return {
            "success": False,
            "message": f"답변 저장 중 오류가 발생했습니다: {str(e)}"
        }
    finally:
        db.close()