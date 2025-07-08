from db.db import SessionLocal
from db.crud import (
    get_all_couple_ids,
    get_users_by_couple_id,
    get_week_chat_logs_by_couple_id,
    get_questionnaire,
    get_daily_emotions,
)
from services.ai import analyzer


def run_weekly_analysis_for_couple(couple_id: str):
    db = SessionLocal()

    try:
        users = get_users_by_couple_id(db, couple_id)  # returns list[User]
        if not users or len(users) != 2:
            print(f"[Couple {couple_id}] 유효하지 않은 유저 수 - 분석 생략")
            return

        user_data = []
        for user in users:
            questionnaire = get_questionnaire(db, user.id)
            daily_logs = get_daily_emotions(db, user.id)

            if not questionnaire and not daily_logs:
                print(f"[User {user.id}] 분석 가능한 데이터 없음 - 생략")

            # 일부 데이터가 없을 때 경고 로그 출력
            if not questionnaire:
                print(f"[User {user.id}] 설문 응답 없음")
                questionnaire_traits = "설문 응답 없음 - 분석 생략"
            else:
                questionnaire_traits = (
                analyzer.analyze_questionnaire(questionnaire.answers)
                if questionnaire else None
            )
            if not daily_logs:
                print(f"[User {user.id}] 감정 기록 없음")
                emotions_summary = "감정 기록 없음 - 분석 생략"
            else:
                emotions_summary = (
                    analyzer.analyze_daily_emotion("\n".join(log.summary for log in daily_logs))
                    if daily_logs else None
                )

            user_data.append({
                "user_id": user.id,
                "questionnaire_traits": questionnaire_traits,
                "emotions_summary": emotions_summary,
            })

        # 커플 채팅 기록 조회 (couple 단위)
        chat_logs = get_week_chat_logs_by_couple_id(db, couple_id)
        if not chat_logs:
            print(f"[Couple {couple_id}] 채팅 기록 없음 - 분석 생략")
            chat_traits = "채팅 기록 없음 - 분석 생략"
        else:
            chat_text = "\n".join(log.content for log in chat_logs) 
            chat_traits = analyzer.analyze_chat(chat_text)

        user1_data, user2_data = user_data[0], user_data[1]

        weekly_solution = analyzer.generate_weekly_solution(
            chat_traits=chat_traits,
            user1_data=user1_data,
            user2_data=user2_data,
        )

        print(f"[Couple {couple_id}] 주간 커플 솔루션\n{weekly_solution}")
        # 예시: 커플 기준 저장
        # from models.db_models import WeeklySolution
        # db.add(WeeklySolution(couple_id=couple_id, content=weekly_solution))
        # db.commit()
    finally:
        db.close()


def run_all_couples_weekly_analysis():
    db = SessionLocal()
    try:
        couple_ids = get_all_couple_ids(db)  # returns list[str] of couple_id
        for (couple_id,) in couple_ids:  # unpacking if query returns list of tuples
            run_weekly_analysis_for_couple(couple_id)
    finally:
        db.close()


if __name__ == "__main__":
    run_all_couples_weekly_analysis()
