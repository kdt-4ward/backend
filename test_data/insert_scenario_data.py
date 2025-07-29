import json
import os
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import bcrypt
from db.db import SessionLocal, engine
from db.db_tables import Base, User, Couple, AIMessage, Message, UserSurveyResponse, SurveyQuestion, SurveyChoice

def init_database():
    Base.metadata.create_all(bind=engine)

def load_json_file(file_path):
    """JSON 파일을 로드합니다."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def insert_scenario_data():
    """시나리오 폴더의 모든 JSON 데이터를 데이터베이스에 삽입합니다."""
    
    # 데이터베이스 세션 생성
    db = SessionLocal()
    
    try:
        survey_choices, question_code_to_id = insert_question_data(db)
        # 커플별 데이터 매핑
        couple_data = {
            "Couple1": {
                "user_ids": ["5942", "1837"],
                "couple_id": "1294",
                "names": ["지민", "상훈"]  # 임시 이름
            },
            "Couple2": {
                "user_ids": ["9275", "4301"],
                "couple_id": "3508",
                "names": ["병준", "수아"]  # 임시 이름
            },
            "Couple3": {
                "user_ids": ["9275", "4301"],  # Couple2와 동일한 유저
                "couple_id": "3508",
                "names": ["병준", "수아"]  # 임시 이름
            },
            "Couple4": {
                "user_ids": ["3168", "7820"],
                "couple_id": "8671",
                "names": ["민준", "혜진"]  # 임시 이름
            }
        }
        
        # 1. User 테이블에 데이터 삽입
        print("1. User 테이블에 데이터 삽입 중...")
        users_to_insert = []
        for couple_name, data in couple_data.items():
            if couple_name == "Couple3":
                continue
            for i, user_id in enumerate(data["user_ids"]):
                # 이미 존재하는지 확인
                existing_user = db.query(User).filter_by(user_id=user_id).first()
                if not existing_user:
                    user = User(
                        user_id=user_id,
                        name=data["names"][i],
                        email=f"{user_id}@test.com",
                        password=bcrypt.hashpw("1234".encode(), bcrypt.gensalt()).decode(),
                        created_at=datetime.utcnow() - timedelta(days=20)
                    )
                    users_to_insert.append(user)
        
        if users_to_insert:
            db.add_all(users_to_insert)
            db.commit()
            print(f"✅ {len(users_to_insert)}명의 사용자가 추가되었습니다.")
        else:
            print("✅ 모든 사용자가 이미 존재합니다.")
        
        # 2. Couple 테이블에 데이터 삽입
        print("2. Couple 테이블에 데이터 삽입 중...")
        couples_to_insert = []
        for couple_name, data in couple_data.items():
            # Couple2와 Couple3는 동일한 커플이므로 Couple2만 처리
            if couple_name == "Couple3":
                continue
                
            existing_couple = db.query(Couple).filter_by(couple_id=data["couple_id"]).first()
            if not existing_couple:
                couple = Couple(
                    couple_id=data["couple_id"],
                    user_1=data["user_ids"][0],
                    user_2=data["user_ids"][1],
                    created_at=datetime.utcnow() - timedelta(days=20)
                )
                couples_to_insert.append(couple)
        
        if couples_to_insert:
            db.add_all(couples_to_insert)
            db.commit()
            print(f"✅ {len(couples_to_insert)}개의 커플이 추가되었습니다.")
        else:
            print("✅ 모든 커플이 이미 존재합니다.")
        
        # 3. 각 커플 폴더의 JSON 파일들을 처리
        scenario_path = "test_data/scenario"
        
        for couple_folder in ["Couple1", "Couple2", "Couple3", "Couple4"]:
            print(f"3. {couple_folder} 데이터 처리 중...")
            folder_path = os.path.join(scenario_path, couple_folder)
            
            if not os.path.exists(folder_path):
                print(f"⚠️ {folder_path} 폴더가 존재하지 않습니다.")
                continue
            if couple_folder not in couple_data:
                continue
            couple_info = couple_data[couple_folder]
            
            # AI 메시지 처리
            ai_messages_file = os.path.join(folder_path, f"AI_chatBot_messages{couple_folder[-1]}.json")
            if os.path.exists(ai_messages_file):
                print(f"   - AI 메시지 처리 중: {ai_messages_file}")
                ai_messages_data = load_json_file(ai_messages_file)
                insert_ai_messages(db, ai_messages_data, couple_info["couple_id"])
            
            # 커플 메시지 처리
            couple_messages_file = os.path.join(folder_path, f"couple_messages_sample{couple_folder[-1]}.json")
            if os.path.exists(couple_messages_file):
                print(f"   - 커플 메시지 처리 중: {couple_messages_file}")
                couple_messages_data = load_json_file(couple_messages_file)
                insert_couple_messages(db, couple_messages_data, couple_info["couple_id"])
            
            
            # 사용자 설문 응답 처리
            survey_responses_file = os.path.join(folder_path, f"user_survey_responses{couple_folder[-1]}.json")
            if os.path.exists(survey_responses_file):
                print(f"   - 설문 응답 처리 중: {survey_responses_file}")
                survey_responses_data = load_json_file(survey_responses_file)
                insert_survey_responses(db, survey_responses_data, survey_choices, question_code_to_id)
        
        print("✅ 모든 시나리오 데이터 삽입이 완료되었습니다!")
        
    except Exception as e:
        db.rollback()
        print(f"❌ 데이터 삽입 중 오류 발생: {e}")
        raise
    finally:
        db.close()

def insert_ai_messages(db: Session, messages_data: list, couple_id: str):
    """AI 메시지를 데이터베이스에 삽입합니다."""
    ai_messages_to_insert = []
    
    for msg_data in messages_data:
        # 이미 존재하는지 확인 (user_id, couple_id, content, created_at으로 중복 체크)
        existing_msg = db.query(AIMessage).filter_by(
            user_id=msg_data["user_id"],
            couple_id=msg_data["couple_id"],
            content=msg_data["content"],
            created_at=datetime.fromisoformat(msg_data["created_at"]) - timedelta(days=10)
        ).first()
        
        if not existing_msg:
            ai_message = AIMessage(
                user_id=msg_data["user_id"],
                couple_id=msg_data["couple_id"],
                role=msg_data["role"],
                content=msg_data["content"],
                created_at=datetime.fromisoformat(msg_data["created_at"]) - timedelta(days=10),
                embed_index=msg_data.get("embed_index"),
                name=msg_data.get("name", None)
            )
            ai_messages_to_insert.append(ai_message)
    
    if ai_messages_to_insert:
        db.add_all(ai_messages_to_insert)
        db.commit()
        print(f"   ✅ {len(ai_messages_to_insert)}개의 AI 메시지가 추가되었습니다.")
    else:
        print("   ✅ 모든 AI 메시지가 이미 존재합니다.")

def insert_couple_messages(db: Session, messages_data: list, couple_id: str):
    """커플 메시지를 데이터베이스에 삽입합니다."""
    couple_messages_to_insert = []
    
    for msg_data in messages_data:
        # 이미 존재하는지 확인 (couple_id, user_id, content, created_at으로 중복 체크)
        existing_msg = db.query(Message).filter_by(
            couple_id=msg_data["couple_id"],
            user_id=msg_data["user_id"],
            content=msg_data["content"],
            created_at=datetime.fromisoformat(msg_data["created_at"]) - timedelta(days=10)
        ).first()
        
        if not existing_msg:
            message = Message(
                couple_id=msg_data["couple_id"],
                user_id=msg_data["user_id"],
                content=msg_data["content"],
                created_at=datetime.fromisoformat(msg_data["created_at"]) - timedelta(days=10),
                is_delivered=msg_data.get("is_delivered", True)
            )
            couple_messages_to_insert.append(message)
    
    if couple_messages_to_insert:
        db.add_all(couple_messages_to_insert)
        db.commit()
        print(f"   ✅ {len(couple_messages_to_insert)}개의 커플 메시지가 추가되었습니다.")
    else:
        print("   ✅ 모든 커플 메시지가 이미 존재합니다.")

def insert_question_data(db: Session):
    with open("test_data/relationship_survey_sets_with_custom.json", "r", encoding="utf-8") as f:
        question_sets = json.load(f)
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

    if survey_questions:
        db.add_all(survey_questions)
        db.commit()
        print(f"   ✅ {len(survey_questions)}개의 설문 문항이 추가되었습니다.")
    if survey_choices:
        db.add_all(survey_choices)
        db.commit()
        print(f"   ✅ {len(survey_choices)}개의 설문 선택지가 추가되었습니다.")
    
    return survey_choices, question_code_to_id

def insert_survey_responses(db: Session, responses_data: list, survey_choices: list, question_code_to_id: dict):
    """사용자 설문 응답을 데이터베이스에 삽입합니다."""
    survey_responses_to_insert = []

    for resp_data in responses_data:
        # 이미 존재하는지 확인 (user_id, question_id로 중복 체크)
        existing_resp = db.query(UserSurveyResponse).filter_by(
            user_id=resp_data["user_id"],
            question_id=resp_data["question_id"]
        ).first()
        
        if not existing_resp:
            choice_id = resp_data["choice_id"] + (resp_data["question_id"] - 1) * 6
            survey_response = UserSurveyResponse(
                user_id=resp_data["user_id"],
                question_id=resp_data["question_id"],
                choice_id=choice_id,
                custom_input=resp_data.get("custom_input")
            )
            survey_responses_to_insert.append(survey_response)
    
    if survey_responses_to_insert:
        db.add_all(survey_responses_to_insert)
        db.commit()
        print(f"   ✅ {len(survey_responses_to_insert)}개의 설문 응답이 추가되었습니다.")
    else:
        print("   ✅ 모든 설문 응답이 이미 존재합니다.")

if __name__ == "__main__":
    insert_scenario_data() 