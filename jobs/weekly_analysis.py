from core.db import SessionLocal
from db.crud import (
    get_all_user_ids,
    get_week_chat_logs,
    get_questionnaire,
    get_daily_emotions,
)
from services.ai import analyzer

def run_weekly_analysis_for_user(user_id: int):
    db = SessionLocal()
    try:
        # 1. 데이터 불러오기
        chat_logs = get_week_chat_logs(db, user_id)
        questionnaire = get_questionnaire(db, user_id)
        daily_logs = get_daily_emotions(db, user_id)

        if not chat_logs or not questionnaire or not daily_logs:
            print(f"[User {user_id}] 데이터 부족 - 분석 생략")
            return

        chat_text = "\n".join(log.content for log in chat_logs)
        daily_summary = "\n".join(log.summary for log in daily_logs)

        # 2. Langchain 기반 분석
        chat_traits = analyzer.analyze_chat(chat_text)
        questionnaire_traits = analyzer.analyze_questionnaire(questionnaire.answers)
        emotions_summary = analyzer.analyze_daily_emotion(daily_summary)

        weekly_solution = analyzer.generate_weekly_solution(
            chat_traits=chat_traits,
            questionnaire_traits=questionnaire_traits,
            daily_emotions=emotions_summary,
        )

        # 3. 결과 처리 (DB에 저장하거나, 알림 전송 등)
        print(f"[User {user_id}] 주간 솔루션\n{weekly_solution}")

        # 예시: DB에 저장 (WeeklySolution 모델이 있다고 가정)
        # from models.db_models import WeeklySolution
        # db.add(WeeklySolution(user_id=user_id, content=weekly_solution))
        # db.commit()

    finally:
        db.close()

def run_weekly_analysis_for_all_users():
    db = SessionLocal()
    try:
        user_ids = get_all_user_ids(db)
        for user_id in user_ids:
            run_weekly_analysis_for_user(user_id)
    finally:
        db.close()

if __name__ == "__main__":
    run_weekly_analysis_for_all_users()
