Tu aides à créer des indices imaginatifs et difficiles pour un jeu de devinettes. Un autre générateur recevra le mot secret, une proposition du joueur, tes termes interdits et tes conseils. Il devra relier la proposition au secret en une phrase indirecte. Le joueur réunira plusieurs indices pour trouver la réponse.

Pour le mot secret, fournis un objet JSON avec :
- "sens" : décris brièvement ses sens courants de nom commun, y compris plusieurs sens distincts lorsqu'ils existent. Pour VOL, le déplacement dans les airs et l'acte de dérober sont tous deux valables. Ces exemples ne constituent pas une liste exhaustive ou exclusive. Exclus les emplois verbaux et adjectivaux, les noms propres et les sens obscurs.
- "mots_interdits" : le mot secret et une liste concise de termes trop révélateurs et de synonymes proches qui rendraient un indice trop facile. N'interdis pas tout un sens ni toutes les associations utiles ; ne donne que les termes nécessaires.
- "conseils" : un court paragraphe créatif proposant des situations ou associations concrètes et variées à travers les sens disponibles du nom. Signale les descriptions particulièrement révélatrices, y compris les périphrases évidentes, sans interdire des sens entiers ni des sujets généraux. Ces pistes sont des sources d'inspiration, pas une liste à suivre : chaque indice doit être naturellement et véritablement lié à la proposition du joueur. Évite de cumuler les détails révélateurs.

Réponds uniquement en JSON : {"sens": "...", "mots_interdits": ["..."], "conseils": "..."}.

Mot secret : « {{word}} ».
