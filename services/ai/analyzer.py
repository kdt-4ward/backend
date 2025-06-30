from langchain.chains import LLMChain
from langchain.chat_models import ChatOpenAI
from .prompt_templates import (
    chat_summary_prompt, questionnaire_prompt,
    daily_emotion_prompt, weekly_solution_prompt
)

llm = ChatOpenAI(model="gpt-4o", temperature=0.7)

chat_summary_chain = LLMChain(llm=llm, prompt=chat_summary_prompt)
questionnaire_chain = LLMChain(llm=llm, prompt=questionnaire_prompt)
daily_emotion_chain = LLMChain(llm=llm, prompt=daily_emotion_prompt)
weekly_solution_chain = LLMChain(llm=llm, prompt=weekly_solution_prompt)


def analyze_chat(chat_text: str):
    return chat_summary_chain.run({"text": chat_text})


def analyze_questionnaire(user_answers: str):
    return questionnaire_chain.run({"user_answers": user_answers})


def analyze_daily_emotion(log_text: str):
    return daily_emotion_chain.run({"daily_log": log_text})


def generate_weekly_solution(chat_traits, user1_data, user2_data):
    return weekly_solution_chain.run({
            "chat_traits": chat_traits or "",
            "user1_questionnaire_traits": user1_data["questionnaire_traits"] or "",
            "user1_daily_emotions": user1_data["emotions_summary"] or "",
            "user2_questionnaire_traits": user2_data["questionnaire_traits"] or "",
            "user2_daily_emotions": user2_data["emotions_summary"] or "",
        })