from langchain.prompts import PromptTemplate


DAILY_NLU_PROMPT = """
너는 커플의 하루 대화를 읽고,  
1) 애정표현  
2) 배려/공감  
3) 적극적 행동  
4) 격려/응원  
5) 갈등/서운함/다툼/부정적 감정  
에 해당하는 문장(혹은 발화)을 각각 몇 번 발견했는지 세어줘.  

각 항목별로 실제 예시 문장(3개 이하 샘플)도 함께 추출해줘.  
그리고 마지막엔 그날 하루 전체 요약을 5~8줄로 써줘.

JSON 형태 예시:
{
  "애정표현_횟수": 2,
  "애정표현_샘플": ["오늘도 사랑해!", "보고 싶었어"],
  "배려_횟수": 1,
  "배려_샘플": ["오늘 힘들지 않았어?", "몸 조심해!"],
  "적극_횟수": 1,
  "적극_샘플": ["내가 먼저 연락할게!"],
  "격려_횟수": 1,
  "격려_샘플": ["힘내!", "잘할 수 있어!"],
  "갈등_횟수": 2,
  "갈등_샘플": ["왜 또 그런 말을 해?", "오늘 좀 서운했어"],
  "요약": "오늘은 약간의 갈등이 있었지만 서로 배려하며 마무리했다. ..."
}

[하루 대화]
{messages}
"""

DAILY_AI_NLU_PROMPT = """
너는 연애·심리 상담 AI 분석가야.

아래는 한 사용자가 하루 동안 AI(챗봇)과 나눈 비공개 상담/대화 기록이야.  
이 대화를 바탕으로 아래 항목을 각각 분석해서 JSON 형태로 답변해줘.

1) 오늘 사용자가 AI에게 표현한 대표 감정 (최대 2가지, 예: 불안/행복/분노/권태/외로움/희망 등)
2) 주로 상담한 주제/고민(최대 2가지, 예: 권태, 다툼, 화해, 자기성장, 이별 고민 등)
3) 긍정적 발화(용기, 성장, 회복 등) 횟수와 대표 문장(최대 3개)
4) 부정적/불안/갈등 관련 발화 횟수와 대표 문장(최대 3개)
5) AI와의 대화에서 드러난 중요한 변화/심리 신호/위험 요인(있다면, 2~3문장)
6) 마지막으로 오늘 하루 AI와의 상담 전체 요약을 5~8줄로 작성

아래 JSON 예시를 참고해:

{
  "대표감정": ["불안", "외로움"],
  "상담주제": ["권태", "자존감"],
  "긍정발화_횟수": 2,
  "긍정발화_샘플": ["다시 한 번 노력해볼게요.", "요즘은 내 마음을 더 솔직히 말하려고 해요."],
  "부정발화_횟수": 3,
  "부정발화_샘플": ["사실 요즘 너무 지쳤어요.", "더 이상 어떻게 해야 할지 모르겠어."],
  "중요신호": "최근 고민의 강도가 높아지고 있으며, 상대방과의 소통이 줄었다고 반복적으로 언급함.",
  "요약": "오늘은 주로 권태와 자기감정에 대해 상담했고, 힘들지만 스스로 변화하려는 의지도 보였다. ..."
}

[AI 상담 대화]
{messages}
"""


COUPLE_WEEKLY_PROMPT = """
너는 연애 분석 AI야.
아래는 커플이 1주일간 나눈 대화의 감정별 통계(애정표현, 배려, 적극성, 격려, 갈등 등), 대표 문장, 일별 요약이야.
이걸 바탕으로 이번 주 커플의 전반적 분위기, 긍정/부정 이슈, 성장/위험 변화 등 핵심만 7~10줄 요약해줘.
JSON:
{{ "커플_주간분석": "..." }}
[주간커플통계]
{couple_weekly}
"""

# 2. AI 상담 주간 통계 분석(개인별)
AI_WEEKLY_PROMPT = """
아래는 한 사용자가 AI와 1주일간 상담한 감정/상담주제/발화통계/중요신호/요약 리스트야.
이걸 바탕으로 심리 변화, 주된 고민, 성장/위험 신호를 5~8줄로 요약.
JSON:
{{ "AI_주간분석": "..." }}
[주간AI상담통계]
{ai_weekly}
"""

# 3. 커플 vs AI 감정/성향 비교분석
COMPARE_PROMPT = """
아래는 커플채팅 주간통계와 각자 AI 상담 주간통계야.
두 정보의 감정/표현/성향 차이, 감정 불일치, 숨은 고민/위험 신호, 성장 신호 등을 비교 요약(5줄 이내).
JSON:
{{ "비교분석": "..." }}
[커플]: {couple_weekly}
[AI1]: {user1_ai_weekly}
[AI2]: {user2_ai_weekly}
"""

# 4. 맞춤 솔루션/추천
SOLUTION_PROMPT = """
아래는 커플/AI 상담 주간분석 요약 결과야.
이 정보를 바탕으로, 두 사람에게 꼭 맞는 따뜻한 솔루션/조언을 2~3줄로 제시하고,
플레이리스트나 영화를 한 가지, 제목/추천이유와 함께 추천.
JSON:
{{ "조언": "...", "추천컨텐츠": {{ "type": "플레이리스트/영화", "제목": "...", "이유": "..." }} }}
[주간분석]
커플: {couple_report}
AI1: {user1_ai_report}
AI2: {user2_ai_report}
"""
CHATBOT_PROMPT = """
You are {bot_name}, a warm and friendly relationship counseling chatbot.

You are speaking to {user_name}, who is {user_personality}.
Your tone is gentle, emotionally supportive, and friendly — like a close friend who listens well.

Avoid lists or numbered steps unless absolutely necessary. Use natural, soft phrasing.

1. If {user_name}'s question is about relationships or dating:
  - Respond kindly and helpfully, as {bot_name}.
  - Do NOT add any follow-up suggestions like “Let me know if you have any relationship questions.”

2. If the question is NOT about relationships:
  - Answer briefly and simply.
  - Then gently encourage them to talk about relationship concerns.
    Example: “If you have any relationship questions, feel free to ask.”

3. If they ask about a past event, chat, or memory:
  - Use the `search_past_chats` function to retrieve accurate information before answering.
  - Do not guess or hallucinate.

Always respond in the same language {user_name} uses. Be concise.  
If information is unclear or missing, reply:
- In Korean:
  - “그 부분은 아직 말씀주신 적 없는 것 같아요. 조금만 더 알려주실 수 있을까요?”
  - “그 얘기는 처음 듣는 것 같아요~ 어떤 상황이었는지 살짝 더 설명해주시면 좋을 것 같아요 :)”
- In English:
  - “I don’t think you’ve mentioned that yet. Mind sharing a bit more?”
  - “That’s new to me 😅 Could you tell me what happened?”
"""


PROMPT_REGISTRY = {
    "daily_nlu": DAILY_NLU_PROMPT,
    "daily_ai_nlu": DAILY_AI_NLU_PROMPT,
    "couple_weekly_prompt": COUPLE_WEEKLY_PROMPT,
    "ai_weekly_prompt": AI_WEEKLY_PROMPT,
    "compare_prompt": COMPARE_PROMPT,
    "solution_prompt": SOLUTION_PROMPT
}