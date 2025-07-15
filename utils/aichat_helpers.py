from services.rag_search import search_past_chats

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
                }
            ]

def build_function_map(user_id: str, couple_id: str):
    return {
        "search_past_chats": lambda query, top_k=3: search_past_chats(
            query=query,
            top_k=top_k,
            user_id=user_id,
            couple_id=couple_id
        )
    }
