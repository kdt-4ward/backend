from datetime import datetime
from db.db_tables import User, Couple, SurveyQuestion, SurveyChoice, UserSurveyResponse, EmotionLog, Message, Base
from db.db import SessionLocal
from db.db_utils import create_database_if_not_exists, drop_database
from db.db import engine
from sqlalchemy import text
import json
from utils.log_utils import get_logger

logger = get_logger(__name__)


def init_database():
    """데이터베이스 초기화 및 테이블 생성"""
    try:
        logger.info("데이터베이스 초기화 시작...")
        
        # 1. 데이터베이스 삭제 후 재생성
        logger.info("기존 데이터베이스 삭제 중...")
        drop_database()
        
        logger.info("새 데이터베이스 생성 중...")
        create_database_if_not_exists()
        
        # 2. 데이터베이스 연결
        from db.db import engine
        
        # 3. 테이블 생성
        logger.info("테이블 생성 중...")
        Base.metadata.create_all(bind=engine)
        
        logger.info("✅ 데이터베이스 초기화 완료!")
        
        # 4. 테이블 존재 확인
        with engine.connect() as conn:
            result = conn.execute(text("SHOW TABLES"))
            tables = [row[0] for row in result]
            logger.info(f"생성된 테이블: {tables}")
            
    except Exception as e:
        logger.error(f"데이터베이스 초기화 실패: {e}")
        raise

def insert_test_data_to_db():
    init_database()
    # ======== 1. 원본 JSON 파일 로딩 =========
    with open("test_data/couple_user_seed_data.json", "r", encoding="utf-8") as f:
        user_data = json.load(f)

    with open("test_data/relationship_survey_sets_with_custom.json", "r", encoding="utf-8") as f:
        question_sets = json.load(f)

    # ======== 2. 유저 및 커플 생성 =========
    users = [
        User(
            user_id=str(u["user_id"]),
            name=u["name"],
            # email=f"user{u['user_id']}@test.com",  # email은 유일해야 하므로 예시
            gender="male" if u["gender"] == "남성" else "female",
            # birth=datetime.now().replace(year=datetime.now().year - u["age"]),
            created_at=datetime.fromisoformat(u["created_at"]),
            profile_image=u.get("profile_image")  # 프로필 이미지가 있다면 추가
        )
        for u in user_data["users"]
    ]

    couple = Couple(
        couple_id=str(user_data["couple"]["couple_id"]),
        user_1=str(user_data["couple"]["user1_id"]),
        user_2=str(user_data["couple"]["user2_id"]),
        created_at=datetime.fromisoformat(user_data["couple"]["started_dating"])
    )

    # ======== 3. 설문 문항 및 선택지 삽입 =========
    survey_questions = []
    survey_choices = []
    question_code_to_id = {}
    qid = 1
    cid = 1

    for qset in question_sets:
        for q in qset["questions"]:
            question = SurveyQuestion(
                id=qid,
                code=q["code"],
                text=q["question"],
                order=qid
            )
            survey_questions.append(question)
            question_code_to_id[q["code"]] = qid

            for c in q["choices"]:
                choice = SurveyChoice(
                    id=cid,
                    question_id=qid,
                    text=c["text"],
                    tag=c["value"]
                )
                survey_choices.append(choice)
                cid += 1

            qid += 1

    # ======== 4. 응답 매핑 함수 =========
    def find_choice_id(code, value):
        for c in survey_choices:
            if c.tag == value and c.question_id == question_code_to_id.get(code):
                return c.id
        return None

    # ======== 5. 유저 응답 생성 =========
    responses = []
    for resp in user_data["trait_responses"]:
        uid = str(resp["user_id"])
        for code, value in resp["responses"].items():
            responses.append(
                UserSurveyResponse(
                    user_id=uid,
                    question_id=question_code_to_id[code],
                    choice_id=find_choice_id(code, value),
                    submitted_at=datetime.utcnow()
                )
            )

    # ======== 6. DB 세션에 삽입 =========
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # 1. 유저 → 커플
    db.add_all(users)
    db.commit()
    db.add(couple)
    db.commit()

    # 2. 설문 문항
    db.add_all(survey_questions)
    db.commit()  # 반드시 커밋해야 choices에서 FK 참조 가능

    # 3. 선택지
    db.add_all(survey_choices)
    db.commit()

    # 4. 유저 응답
    db.add_all(responses)
    db.commit()
    db.close()
        # ======== 7. 감정로그 추가 =========
    with open("test_data/emotion_logs_sample.json", "r", encoding="utf-8") as f:
        emotion_data = json.load(f)

    emotion_logs = [
        EmotionLog(
            user_id=str(entry["user_id"]),
            couple_id=str(entry["couple_id"]) if entry.get("couple_id") else None,
            emotion=entry["emotion"],
            detail_emotions=json.dumps(entry["detail_emotions"]) if entry.get("detail_emotions") else None,
            memo=entry.get("memo"),
            recorded_at=datetime.fromisoformat(entry["recorded_at"]),
            updated_at=datetime.fromisoformat(entry["updated_at"]) if entry.get("updated_at") else datetime.utcnow(),
            deleted_at=datetime.fromisoformat(entry["deleted_at"]) if entry.get("deleted_at") else None,
        )
        for entry in emotion_data
    ]
    db.add_all(emotion_logs)
    db.commit()

    # ======== 8. 커플 메시지 추가 =========
    with open("test_data/couple_messages_sample.json", "r", encoding="utf-8") as f:
        message_data = json.load(f)

    messages = [
        Message(
            couple_id=str(entry["couple_id"]),
            user_id=str(entry["user_id"]),
            content=entry["content"],
            created_at=datetime.fromisoformat(entry["created_at"]),
            is_delivered=entry["is_delivered"]
        )
        for entry in message_data
    ]
    db.add_all(messages)
    db.commit()
    print("✅ Seed data successfully inserted.")

    users = db.query(User).all()
    for user in users:
        print(user.user_id)
        print(user.name)
        print(user.gender)
        print(user.created_at)
        print(user.profile_image)
        print(user.email)
        print(user.birth)
    