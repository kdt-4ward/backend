USER_TRAIT_SUMMARY_PROMPT = """
You are a relationship analyst. Below is a list of relationship-related traits for user:

{trait_list}

Using only the information explicitly mentioned in the list (do not make assumptions), write a concise and natural summary of user's relationship tendencies in no more than 5 sentences. Do not include any traits or insights that are not directly supported by the input.
""" 