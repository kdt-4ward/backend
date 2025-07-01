import json

from models.db_models import Message, EmotionLog
from core.db import SessionLocal

def load_data(data_path):
    with open(data_path, 'r', encoding='utf-8') as rf:
        return json.load(rf)

def insert_data():
    db = SessionLocal()
    data = load_data("/home/leejd/project/lovetune_4ward/back/backend/tests/data/preprocessed/couple_chat_table_0623-0630.json")

    for kwargs in data:
        db.add(Message(**kwargs))
        db.commit()

    data = load_data("/home/leejd/project/lovetune_4ward/back/backend/tests/data/preprocessed/couple_emotion_summary.json")

    for kwargs in data:
        db.add(EmotionLog(**kwargs))
        db.commit()

if __name__=="__main__":
    insert_data()