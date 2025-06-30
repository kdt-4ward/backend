from langchain.prompts import PromptTemplate

chat_summary_prompt = PromptTemplate.from_template("""
다음은 연인 간의 채팅 내용입니다. 이 내용을 바탕으로 두 사람의 성향을 분석하고 요약해 주세요:

{text}
""")

questionnaire_prompt = PromptTemplate.from_template("""
다음은 사용자의 자기소개 및 질문지 응답입니다:

{user_answers}

이 정보를 기반으로 성격 및 연애 성향을 분석해 주세요.
""")

daily_emotion_prompt = PromptTemplate.from_template("""
다음은 하루 동안의 감정 표현 기록입니다:

{daily_log}

감정 상태를 요약하고 주요 요인을 분석해 주세요.
""")

from langchain.prompts import PromptTemplate

weekly_solution_prompt = PromptTemplate.from_template("""
[커플 채팅 기반 성향 분석 요약]
{chat_traits}

[User 1 - 질문지 성향 분석 요약]
{user1_questionnaire_traits}

[User 1 - 일일 감정 요약]
{user1_daily_emotions}

[User 2 - 질문지 성향 분석 요약]
{user2_questionnaire_traits}

[User 2 - 일일 감정 요약]
{user2_daily_emotions}

위의 내용을 바탕으로 두 사람의 감정과 성향을 고려하여,
커플이 서로를 더 잘 이해하고 긍정적인 관계를 유지할 수 있도록
이번 주에 실천할 수 있는 구체적이고 따뜻한 주간 솔루션을 작성해주세요.
""")