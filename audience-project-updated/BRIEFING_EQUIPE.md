# Briefing équipe — Analyse d'Audience & Prédiction

## Le projet en une phrase

On part de logs de visionnage (qui regarde quoi, où il décroche, où il fait pause) pour repérer automatiquement les passages ennuyeux d'une vidéo et prédire si les spectateurs vont continuer à regarder ou abandonner.

## Pourquoi ce découpage en 7 rôles fonctionne

Le projet est une chaîne de transformation de données : chaque personne prend ce que la précédente a produit et l'enrichit. C'est important à comprendre dès le départ parce que ça veut dire qu'on ne peut pas tous coder en même temps sur n'importe quoi — il y a un ordre de dépendances.

```
P1 (logs bruts) → P2 (features par segment) → P3 (zones d'ennui)
                                              ↘
                                                P4/P5 (modèle de prédiction)
                                              ↗
                            P6 (dashboard qui affiche tout ça)
                            P7 (coordonne, documente, prépare le pitch)
```

Concrètement : P3 et P4/P5 ont tous les deux besoin de ce que P2 produit, donc ils peuvent travailler en parallèle une fois que P2 a livré sa table de features. P6 n'a pas besoin d'attendre que tout soit fini — il peut construire son dashboard avec des données factices dès la première heure, puis brancher les vraies sorties au fur et à mesure qu'elles arrivent.

## Ce qui a déjà été construit (point de départ, pas point d'arrivée)

J'ai codé un pipeline complet et fonctionnel pour qu'on ait une base solide dès le début du hackathon plutôt que de partir d'une page blanche. Tout tourne déjà de bout en bout. L'idée n'est pas de le recopier tel quel mais de l'utiliser comme socle : chacun comprend sa partie, l'améliore, et on construit le reste du temps sur quelque chose qui marche déjà plutôt que de risquer de ne rien avoir à présenter à la fin.

Le projet zippé contient :
- les 5 vidéos simulées et ~16 000 événements de visionnage (logs)
- les features calculées par segment de 15 secondes
- les zones d'ennui détectées automatiquement
- un modèle de prédiction entraîné (RandomForest et GradientBoosting comparés)
- un dashboard Streamlit qui affiche tout
- trois éléments en plus du brief de base, dont je parle plus bas

## Comment expliquer chaque partie aux personnes concernées

### Pour P1 (Data)

Le rôle de P1 est de garantir que tout le monde travaille sur un schéma de données identique et propre. J'ai simulé des logs au format `user_id, video_id, session_id, event_type, timestamp_video, timestamp_wall` parce qu'en hackathon on n'a généralement pas accès à de vraies données de plateforme. Si jamais l'équipe a accès à de vraies données quelque part, c'est P1 qui doit les adapter à ce même schéma — le reste du pipeline ne change pas tant que le schéma est respecté. À montrer à P1 : `src/01_generate_logs.py` et la section schéma du README.

### Pour P2 (Features)

Le choix fait ici est de découper les vidéos en segments fixes de 15 secondes plutôt qu'en segments sémantiques (changements de plan, chapitres). C'est un compromis volontaire pour rester simple et rapide à exécuter en temps limité — à assumer si le jury pose la question, ce n'est pas une faiblesse mais un choix de scope. Pour chaque segment, on calcule le taux de complétion, le taux de décrochage, les pauses, replays, seeks. C'est cette table qui sert de carburant à tout le reste. À montrer à P2 : `src/02_build_features.py`.

### Pour P3 (Zones d'ennui)

Volontairement, ce n'est pas du machine learning ici, juste un score composite (décrochage + pauses, pondérés) et un seuillage par percentile. C'est un choix assumé : pas besoin de complexité inutile pour un problème qui se résout bien avec de l'agrégation simple, et ça libère du temps de cerveau pour la partie modèle qui, elle, a vraiment besoin de ML. À montrer à P3 : `src/03_detect_bored_zones.py`, et surtout lui montrer que les zones détectées recoupent bien les vraies zones injectées dans les données simulées — c'est la preuve que l'approche fonctionne avant même de toucher à de vraies données.

### Pour P4/P5 (Modèle & évaluation)

Le point le plus important à clarifier avec ce binôme avant de coder : on prédit en régression (un score continu de rétention) et pas directement en classification, parce que "score de rétention" suggère un continu plutôt qu'un oui/non. La classification (pour la matrice de confusion et la ROC demandées dans le brief) est dérivée après coup en seuillant le score prédit. Ça évite de construire deux modèles séparés pour rien.

Un point à leur signaler franchement : le R² obtenu sur les données simulées est très élevé (0.998), ce qui est en partie un artefact parce que la cible est une suite de valeurs décroissantes, donc mécaniquement prévisible d'un segment à l'autre. Plutôt que de cacher ça, on l'a transformé en argument : on a comparé le modèle à une baseline naïve et montré qu'il réduit l'erreur de 52%, ce qui prouve que le modèle apporte une vraie valeur ajoutée et pas juste une corrélation triviale. C'est ce genre de rigueur qui distingue une équipe qui a vraiment compris son sujet d'une équipe qui a juste fait tourner un RandomForest. À montrer : `src/04_train_model.py` et `src/06_baseline_and_explainability.py`.

### Pour P6 (Dashboard)

Le dashboard Streamlit est déjà structuré en sections : métriques clés en haut, puis insights automatiques en langage naturel, puis la courbe de rétention avec les zones d'ennui surlignées sur la timeline, puis le détail par segment, puis une vue d'ensemble multi-vidéos avec les personas de spectateurs et l'explicabilité du modèle. P6 peut commencer à customiser le visuel et l'ergonomie tout de suite, sans attendre que P4/P5 aient fini d'optimiser le modèle — le dashboard lit des fichiers CSV et un modèle déjà sauvegardés, donc il fonctionne dès maintenant avec ce qui existe. À montrer : lancer `streamlit run src/05_dashboard.py` ensemble pour que tout le monde voie le rendu final dès le début, ça motive et ça donne une cible visuelle claire à chacun.

### Pour P7 (Coordination, doc, pitch)

Le rôle le plus important de P7 n'est pas d'écrire de la doc après coup, c'est de verrouiller les définitions AVANT que les autres commencent à coder, pour éviter qu'un decalage de définition entre deux binômes casse l'intégration en fin de hackathon. Le README contient déjà ces définitions (segment, taux de complétion, taux de décrochage, score d'ennui, score de rétention prédit) — à relire en groupe en tout début de session pour s'assurer que tout le monde est aligné, et à customiser si quelqu'un voit une meilleure formulation.

## Les trois éléments ajoutés au-delà du brief minimal

Pour se démarquer en hackathon, on ne se contente pas de répondre au brief, on montre qu'on a réfléchi plus loin. Trois ajouts à présenter au jury comme des choix stratégiques de l'équipe, pas des fioritures :

La comparaison à une baseline naïve répond à la question que tout jury technique pose tôt ou tard : "pourquoi du ML et pas juste des règles ?" On a la réponse chiffrée avant qu'on nous la pose.

Le clustering de personas de spectateurs (Engagé fluide, Décrocheur rapide, Zappeur...) montre qu'on raisonne aussi sur qui regarde, pas seulement sur le pourcentage qui décroche. Ça enrichit le récit du pitch au-delà d'une simple courbe.

Le générateur d'insights automatiques transforme les chiffres en phrases actionnables affichées directement dans le dashboard (ex: "zone critique entre 90s et 165s, à raccourcir en priorité"). C'est l'argument produit : on ne livre pas juste un modèle, on livre un outil qu'un créateur de contenu peut utiliser sans savoir lire une matrice de confusion.

## Comment lancer la première réunion d'équipe

Suggestion de déroulé pour les 15-20 premières minutes, avant que tout le monde se disperse sur son rôle :

D'abord, lancer le dashboard ensemble (`streamlit run src/05_dashboard.py`) pour que tout le monde voie la cible finale — ça aligne les attentes visuelles et donne de l'énergie au groupe. Ensuite, relire à voix haute les définitions clés du README pour s'assurer qu'il n'y a pas d'ambiguïté entre binômes. Puis chaque binôme regarde rapidement son fichier source dédié pendant que P7 prend des notes sur les questions ou améliorations qui ressortent. Enfin, on fixe ensemble 2-3 jalons horaires (par exemple : H+2 features prêtes si on modifie quelque chose, H+5 modèle final, H+7 dashboard branché, dernière heure pitch) pour que personne ne soit surpris en fin de journée.

## Fichiers à connaître

Le zip contient tout, organisé par rôle. Le README à la racine est le document de référence — c'est lui qui fait foi en cas de désaccord sur une définition ou un format de données.
