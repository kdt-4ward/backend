# Import from separated prompt files
from .prompts.chatbot.persona import CHATBOT_PROMPT_EN, CHATBOT_PROMPT_KO
from .prompts.analysis.daily import DAILY_NLU_PROMPT, DAILY_AI_NLU_PROMPT, DAILY_COMPARISON_PROMPT
from .prompts.analysis.weekly import (
    COUPLE_WEEKLY_PROMPT, 
    AI_WEEKLY_PROMPT, 
    COMPARE_PROMPT, 
    SOLUTION_PROMPT
)
from .prompts.user_trait import USER_TRAIT_SUMMARY_PROMPT

################### 프롬프트 등록 #####################
PROMPT_REGISTRY = {
    "daily_nlu": DAILY_NLU_PROMPT,
    "daily_ai_nlu": DAILY_AI_NLU_PROMPT,
    "couple_weekly_prompt": COUPLE_WEEKLY_PROMPT,
    "ai_weekly_prompt": AI_WEEKLY_PROMPT,
    "compare_prompt": COMPARE_PROMPT,
    "solution_prompt": SOLUTION_PROMPT,
    "user_trait_summary_prompt": USER_TRAIT_SUMMARY_PROMPT,
    "chatbot_prompt_en": CHATBOT_PROMPT_EN,
    "chatbot_prompt_ko": CHATBOT_PROMPT_KO,
    "daily_comparison_prompt": DAILY_COMPARISON_PROMPT
}
