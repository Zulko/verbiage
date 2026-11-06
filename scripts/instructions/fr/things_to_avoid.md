Tu es spécialiste des jeux de mots comme le Taboo. Le joueur doit deviner un mot secret, et les indices ne doivent pas rendre la réponse trop facile.

Un autre générateur recevra le mot secret, son sens attendu, une proposition du joueur, ta liste de mots interdits et tes conseils. Pour chaque proposition, il écrira une phrase indirecte reliant cette proposition au mot secret, sans révéler ce dernier. Le joueur trouvera la réponse en réunissant plusieurs indices.

**Ta tâche :** Pour le mot secret pris dans son sens courant de nom commun, fournis un objet JSON avec trois clés :

- `"sens"` : une description concise et sans ambiguïté du sens de nom commun retenu, qui le distingue des autres sens et des emplois comme verbe ou adjectif. Par exemple, pour VOL, précise s'il s'agit d'un déplacement dans les airs ou d'un acte de vol.
- `"mots_interdits"` : une liste d'environ 20 mots fortement associés au mot secret qui ne doivent pas apparaître dans les indices. Inclus le mot secret et d'autres termes évidents qui rendraient la réponse trop facile.
- `"conseils"` : un court paragraphe de 3 à 5 phrases pour aider à créer des indices difficiles et imaginatifs. Identifie les caractéristiques, usages ou associations les plus révélateurs à ne pas décrire directement, y compris par des périphrases qui évitent les mots interdits. Propose ensuite plusieurs situations, actions ou associations concrètes et variées qui pourraient inspirer des indices informatifs et indirects, tout en restant fidèles au sens retenu du nom. Laisse la place à des liens précis au lieu d'interdire des sujets entiers ou d'encourager des traits vagues. Ces pistes sont des sources d'inspiration, pas des thèmes imposés : chaque indice doit être naturellement lié à la proposition du joueur. Évite les sens obscurs, les noms propres et l'accumulation de détails révélateurs.

**Format :** Réponds uniquement en JSON, sans texte supplémentaire :
`{ "sens": "...", "mots_interdits": [...], "conseils": "..." }`

**Exemples :**

Pour le mot secret « chien » :
```json
{
  "sens": "Un animal domestique de la famille des canidés, souvent compagnon ou auxiliaire de l'être humain.",
  "mots_interdits": ["chien", "aboyer", "queue", "patte", "os", "chiot", "canin", "ouaf", "animal", "rapporter", "niche", "fourrure", "laisse", "limier", "renifler", "sifflet", "garder", "fidèle", "compagnon", "race"],
  "conseils": "Évite de décrire directement un animal domestique qui aboie, se promène en laisse ou rapporte un bâton. Des indices indirects pourraient évoquer la compagnie, les habitudes quotidiennes ou l'accueil d'un visiteur à la porte. Utilise ces pistes comme points de départ et relie chaque indice à la proposition du joueur."
}
```

Pour le mot secret « couleur » :
```json
{
  "sens": "Une qualité visuelle comme le rouge, le bleu ou le vert.",
  "mots_interdits": ["couleur", "teinte", "ton", "pinceau", "palette", "arc-en-ciel", "spectre", "vif", "brillant", "pigment", "rouge", "bleu", "vert", "jaune", "chromatique", "nuance", "colorant", "prisme", "peinture", "visuel"],
  "conseils": "Évite de décrire directement ce qui fait paraître les objets rouges ou bleus, les bandes visibles après la pluie ou le mélange de peintures. Des pistes indirectes pourraient évoquer la façon dont un objet se détache de son entourage ou la manière de décrire une humeur. Choisis une piste qui convient à la proposition sans accumuler les détails révélateurs."
}
```

Maintenant, à toi ! Le mot secret est « {{word}} ».
