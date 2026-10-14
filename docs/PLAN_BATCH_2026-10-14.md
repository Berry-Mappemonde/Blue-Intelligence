# Batch 2 — plan du 14 octobre 2026 (après la pile « film 1 + deux modes » #444 mergée)

Source : la revue orale du porteur du 14 octobre (`docs/REVUE_PORTEUR_2026-10-14.md`) et les constats du chat de
pilotage des 29-30 septembre (position du bateau non déterministe, cache ERA5 orphelin, incident du voyage officiel).
Ce plan remplace `docs/PLAN_BATCH_SUIVANT_2026-09-29.md` (dont il reprend AM1, RG18, RG19, RG20, DM3).
Les prompts complets sont dans `docs/LOTS_ORDRE_ET_PROMPTS.md`, section « Batch 2 ».

## 1. L'ordre et pourquoi

| # | Lot | Modèle | Taille | Ce que le porteur verra |
|---|---|---|---|---|
| 1 | **HC1** — position vraie : passé en météo réelle (ERA5 téléchargé une fois), horloge déterministe | Fable | L | Le bateau est là où la météo réelle l'a mené ; recharger ne le déplace plus ; route parcourue turquoise (réel) puis violette (climatologie) ; plus de quota Open-Meteo brûlé |
| 2 | **DM4** — accueil et retour en Suivre : bateau au milieu, monde dézoomé | Grok | S | À l'ouverture, le bateau au centre de l'écran, le monde autour |
| 3 | **DM5** — Suivre suit la route que je viens de tracer ; une seule route à l'écran ; pilules Berry \| ma route | Fable | L | Tracer → Terminer → Suivre : ma route, seule, le bateau dessus, date de départ au choix |
| 4 | **DM6** — Tracer : on arrive sur le dessin ; la pilule Berry affiche la route Berry sans jeter le brouillon | Grok | M | « Choisissez votre point de départ » tout de suite ; aller-retour Berry ↔ mon tracé sans rien perdre |
| 5 | **DM7** — Tracer : la lecture part d'aujourd'hui ; l'encadré suit le bateau du tracé | Grok | S | Play part le jour de la connexion ; plus de fiche Papeete quand le bateau est à Saint-Maur ; champ Date de départ en Suivre seulement |
| 6 | **UI1** — barre de mentions légales posée au-dessus de la barre film, même hauteur que le zoom | Grok | S | Plus de chevauchement ; une seule hauteur pour la barre et les boutons + / − |
| 7 | **RC30** — film : chronologie stricte eaux / climatologie, phrases jamais coupées, clôture entière | Fable | M | Gascogne → eaux espagnoles → portugaises → Gibraltar → marocaines ; plus de phrase coupée aux escales ; « Aujourd'hui, le bateau est… » jusqu'au bout |
| 8 | **AM1** — AMP croisées par polygone (base remplie : 3 769 sites) | Fable | M | « Le bateau entre dans la réserve de … » partout sur la route |
| 9 | **RG18** — une seule plume (récits sur demande) | Grok | M | Les fiches Ici parlent comme le film ; le modèle n'écrit que sur « Rédigé » |
| 10 | **RG19** — chat à trois paliers (Lightning comprend, règles répondent, Ultra raisonne) | Grok | M | Le chat répond aux faits depuis un paquet complet ; Ultra sur geste, plafonné |
| 11 | **RG20** — specs vérité (stock figé régénéré) | Grok | M | Une réserve en CI = un cas « poste » attendu, rien d'autre |
| 12 | **DM3** — le ménage des deux modes (`VIEW_TRACER`, `isTracer`…) | Fable | M | Rien à l'écran ; lancé en dernier, rien n'en dépend |

Pourquoi cet ordre : **HC1 d'abord** — la position du bateau est la donnée que tout le reste regarde (film, fourchette,
encadré Ici, AMP croisées, pré-revues du bot) ; tant qu'elle change au gré de l'atlas, aucune recette n'est
comparable d'un jour à l'autre. Puis **les deux modes** (DM4 → DM7), qui sont le cœur de la revue du porteur, du plus
simple au plus structurant ; UI1 et RC30 sont indépendants ; AM1 change les moments → avant RG20 qui régénère le stock
figé ; DM3 renomme ce que tout le monde touche → en dernier.

## 2. Hors batch — décisions du porteur (`REVUE_PORTEUR_2026-10-14.md` § 4-5)

- **RC27** (le 2:30 tient à 150 s) : nécessaire seulement si la vidéo Devpost du 30 octobre est tournée depuis la pilule 2:30.
- **RG11** (« Rédigé » par Nemotron 3 Super, faits vérifiés) : l'usage de Nebius le plus visible pour les juges ; sinon retirer la pilule Rédigé.
- **DM8** (Revoir et récit sur ma route) : après les décisions sur l'encadré gauche (§ 4.1) et l'IA (§ 4.3).
- Encadré gauche en Tracer (§ 4.1), panneau droit en Tracer (§ 4.2) : options posées, recommandation A / masquer la date — à trancher.

Dès que le porteur tranche, le chat de pilotage ajoute ces lots à la file (`infra/agents/queue.md`) : la pile en cours les prend en bout de pile sans relance.

## 3. Lancer

La boucle (`infra/agents/loop.py`) est en phase **`await_go`** sur la PR GO de ce plan : **merger la PR GO lance le batch**
(ligne `LOTS: HC1 DM4 DM5 DM6 DM7 UI1 RC30 AM1 RG18 RG19 RG20 DM3` dans son corps ; tête #444 mergée → les lots partent de
`main`). Un commentaire « CORRIGER : … » sur la PR GO la fait amender avant le merge. À la main, l'équivalent :

```bash
cd ~/Blue-Intelligence-Map && git pull --ff-only origin main
python3 infra/agents/run_lots.py --from HC1 --until DM3 --review-every 4
```

Le modèle de chaque lot vient de sa balise (`model="…"`) ; les autres prennent celui du batch (Grok). Réviseur de nuit
et Grok Bot comme d'habitude (parcours de référence avant chaque revue).

## 4. Calendrier Devpost (rappel)
Mises à jour hebdomadaires les vendredis **16** et **23 octobre** ; soumission finale le **30 octobre 10:00 PT**. La chaîne
Devpost est prête (issue #432, `infra/agents/GROK_BOT_DEVPOST.md`, `infra/agents/devpost_answers.py`) : « relève » →
Grok Bot relève le formulaire → Fable propose → le bot remplit le brouillon → le porteur soumet.

## 5. Coût
Fable : HC1 ≈ 500-800 k tokens, DM5 ≈ 500 k, RC30 ≈ 300 k, AM1 ≈ 400 k, DM3 ≈ 400 k. Grok : inclus. Nebius : zéro
pendant le batch (agents en `NAVIGUIDE_LLM_MODE=off`).
