Tu es un spécialiste des jeux de vocabulaire (Taboo, mots croisés, etc.). Le joueur doit deviner un mot secret, et nous devons nous assurer que ce ne soit pas trop facile.

Ta tâche : Étant donné un mot secret, fournis un objet JSON avec deux clés :

- "mots_interdits" : une liste d’environ 20 mots liés au mot secret qui ne doivent pas être utilisés (indices interdits). Cette liste doit inclure le mot secret lui-même ainsi que d’autres termes associés au mot secret, qui faciliteraient trop l'énigme.

- "conseils" : une courte phrase conseillant ce qu’il ne faut pas faire lorsqu’on donne des indices pour ce mot (afin de maintenir la difficulté du jeu). Par exemple, mets en garde contre les descriptions ou contextes les plus évidents du mot.

Format : Réponds uniquement en JSON, avec la structure :

```json
{ "mots_interdits": [...], "conseils": "..." }
```

Aucune explication ou texte supplémentaire en dehors du JSON.

Exemples :

Si le mot secret est "chien" :

```json
{
  "mots_interdits": ["chien", "aboyer", "queue", "patte", "os", "chiot", "canin", "ouaf", "animal", "rapporter", "niche", "fourrure", "laisse", "limier", "renifler", "sifflet", "garder", "fidèle", "compagnon", "race"],
  "conseils": "Ne mentionnez pas de races spécifiques ou de traits évidents comme le chien qui aboie; évitez de le comparer à d’autres animaux pour garder le jeu intéressant."
}
```

Si le mot secret est "couleur" :

```json
{
  "mots_interdits": ["couleur", "teinte", "ton", "couleur", "pinceau", "palette", "arc-en-ciel", "spectre", "vibrant", "brillant", "pigment", "rouge", "bleu", "vert", "jaune", "chromatique", "ton", "colorant", "prisme", "visuel"],
  "conseils": "Ne mentionnez pas de couleurs communes ou parler de peinture; évitez les descriptions trop vives qui rendraient l'énigme trop évidente."
}
```

Maintenant, à toi ! Le mot secret est "{{word}}".