You are helping create challenging, imaginative clues for a word-guessing game. Another generator will receive the secret word, a player's guess, your forbidden terms, and your advice. It must connect the guess to the secret in one indirect sentence. Players combine several clues to find the answer.

Given the secret word, return JSON with:
- "sense": Briefly describe its familiar common-noun meanings, including distinct common meanings where applicable. For BANK, a financial institution and the land beside a river are both valid. These are examples, not an exhaustive or exclusive list. Exclude verb and adjective uses, proper names, and obscure meanings.
- "avoid": The secret word and a concise list of direct giveaways and close synonyms that would make an individual clue too easy. Do not ban a whole meaning or every useful association; use only as many terms as needed.
- "advice": A short, creative paragraph suggesting varied concrete situations or associations across available noun meanings. Flag particularly revealing descriptions, including obvious paraphrases, but do not prohibit entire meanings or broad topics. The suggestions are inspiration, not a checklist; each clue must connect naturally and truthfully to its guess. Avoid stacking giveaway details.

Return only JSON: {"sense": "...", "avoid": ["..."], "advice": "..."}.

Secret word: "{{word}}".
