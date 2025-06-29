from tests.fixtures.test_data import create_dummy_couple

def test_couple_chat_flow(client, db):
    create_dummy_couple(db)

    with client.websocket_connect("/ws/userA") as wsA:
        with client.websocket_connect("/ws/userB") as wsB:
            # 커플 등록
            wsA.send_json({
                "type": "register_couple",
                "partner_id": "userB",
                "couple_id": "coupleAB"
            })

            msg = wsA.receive_json()
            assert msg["type"] == "system"

            # 메시지 전송
            wsA.send_json({
                "type": "message",
                "couple_id": "coupleAB",
                "message": "안녕!",
                "image_url": None
            })

            received = wsB.receive_json()
            assert received["message"] == "안녕!"
