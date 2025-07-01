WINDOW_SIZE = 10
OVERLAP = 4

class HistoryWindowManager:
    @staticmethod
    def should_summarize(history: list) -> bool:
        return len(history) >= WINDOW_SIZE

    @staticmethod
    def get_reference_and_target(history: list) -> tuple[list, list]:
        """
        - 처음엔 참조 없음 → 최신 10개만 요약
        - 이후에는 4턴 참조 + 10턴 요약
        """
        if len(history) < WINDOW_SIZE + OVERLAP:
            reference = []
            target = history[:WINDOW_SIZE]
        else:
            reference = history[:OVERLAP]
            target = history[OVERLAP:OVERLAP + WINDOW_SIZE]
        return reference, target

    @staticmethod
    def slide_window(history: list) -> list:
        return history[WINDOW_SIZE:]