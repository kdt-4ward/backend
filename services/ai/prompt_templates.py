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

weekly_solution_prompt = PromptTemplate.from_template("""
[채팅 기반 성향 분석 요약]
{chat_traits}

[질문지 성향 분석 요약]
{questionnaire_traits}

[일일 감정 요약]
{daily_emotions}

위 내용을 바탕으로 커플에게 유익한 주간 솔루션을 작성해 주세요.
""")
