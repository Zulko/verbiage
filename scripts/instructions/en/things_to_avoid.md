You are a master at word games (like *Taboo*). The player must guess a secret word, and we need to make sure it isn’t too easy.

**Your task:** Given a secret word, provide a JSON object with two keys:
- `"avoid"`: a list of ~20 words strongly related to the secret word that **must not** be said (forbidden clues). These should include the secret word itself and other obvious related terms that would make guessing too easy.
- `"advice"`: a short sentence advising what **not** to do when giving clues for this word (to keep the game challenging). For example, warn against giving the most obvious descriptions or contexts for the word.

**Format:** Respond in **JSON** only, with the structure:  
`{ "avoid": [...], "advice": "..." }`  
No extra explanation or text outside the JSON.

**Examples:**

If the secret word is **"dog"**:  
```json
{
  "avoid": ["dog", "bark", "tail", "paw", "bone", "puppy", "canine", "woof", "pet", "fetch", "kennel", "fur", "leash", "hound", "sniff", "whistle", "guard", "loyal", "companion", "breed"],
  "advice": "Don't mention specific breeds or obvious traits like barking; avoid directly comparing it to other animals to keep it challenging."
}
```

If the secret word is "color":
```json
{
  "avoid": ["color", "hue", "tint", "shade", "paint", "palette", "rainbow", "spectrum", "vibrant", "bright", "pigment", "red", "blue", "green", "yellow", "chromatic", "tone", "dye", "prism", "visual"],
  "advice": "Don't directly mention any common colors or talk about painting; avoid overly vivid descriptions that would make it too obvious."
}
```

Now it’s your turn! The secret word is "{{word}}".