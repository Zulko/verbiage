You are a master at word games (like *Taboo*). The player must guess a secret word, and we need to make sure it isn’t too easy.

Another clue generator will receive the secret word, its intended meaning, a player's guess, your forbidden-word list, and your advice. It must write a single indirect sentence relating the guess to the secret, without revealing the secret. Players combine clues from multiple guesses to find it.

**Your task:** Given a secret word in its usual common-noun sense, provide a JSON object with three keys:
- `"sense"`: a concise, unambiguous description of the intended common-noun meaning, distinguishing it from other parts of speech or unrelated senses. For GRAVE, use a burial place rather than the adjective meaning serious; for BLEND, use a mixture rather than the verb meaning to blend in.
- `"avoid"`: a list of ~20 words strongly related to the secret word that **must not** be said (forbidden clues). These should include the secret word itself and other obvious related terms that would make guessing too easy.
- `"advice"`: write a short paragraph of 3–5 sentences to help another model create challenging, imaginative clues for the secret word. Identify the most revealing traits, uses, and familiar associations that should not be described directly, including ideas that could be expressed without using the forbidden words. Then suggest a few varied, concrete situations, actions, or associations that could inspire informative indirect clues about the intended noun sense. Leave room for specific connections rather than banning broad topics or encouraging vague traits. These are inspiration, not mandatory themes: each clue must still relate naturally to the player’s guess. Avoid obscure senses and proper names, and avoid combining several giveaway details in one clue.

**Format:** Respond in **JSON** only, with the structure:  
`{ "sense": "...", "avoid": [...], "advice": "..." }`
No extra explanation or text outside the JSON.

**Examples:**

If the secret word is **"dog"**:  
```json
{
  "sense": "A domesticated canine kept as a companion or working animal.",
  "avoid": ["dog", "bark", "tail", "paw", "bone", "puppy", "canine", "woof", "pet", "fetch", "kennel", "fur", "leash", "hound", "sniff", "whistle", "guard", "loyal", "companion", "breed"],
  "advice": "Avoid directly describing a household animal that barks, is walked on a leash, or fetches a thrown stick. Indirect clues could draw on companionship, routines, or a visitor being greeted at the door. Use these as starting points, not as a checklist, and relate each clue to the player's guess."
}
```

If the secret word is "color":
```json
{
  "sense": "A visual quality such as red, blue, or green.",
  "avoid": ["color", "hue", "tint", "shade", "paint", "palette", "rainbow", "spectrum", "vibrant", "bright", "pigment", "red", "blue", "green", "yellow", "chromatic", "tone", "dye", "prism", "visual"],
  "advice": "Avoid directly describing what makes objects look red or blue, the bands seen after rain, or mixing paints to make new shades. Indirect clues could explore how objects stand out, how appearances change in different surroundings, or how people describe moods. Choose an angle that fits the guess without piling several identifying details into one clue."
}
```

Now it’s your turn! The secret word is "{{word}}".
