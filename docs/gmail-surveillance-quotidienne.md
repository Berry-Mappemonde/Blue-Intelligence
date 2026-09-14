# Surveillance quotidienne de la boîte Gmail

Compte : la boîte Workspace Berry-Mappemonde déjà reliée à Cursor.  
Fuseau : Nouvelle-Calédonie (UTC+11). Le passage automatique tourne à **07:00 à Nouméa** (`20:00` UTC).

Ce document est la **méthode unique** de classement. Un agent Cursor la rejoue chaque matin. Les règles exécutables sont dans `scripts/gmail/regles.json`.

## Ce qui se passe chaque jour

1. L’agent cherche les fils des **24 dernières heures** (`newer_than:1d`) et tout ce qui est encore dans la boîte **sans libellé** (`in:inbox has:nouserlabels`).
2. Il pose les mêmes libellés qu’au grand rangement : **correspondant + thème + pertinence**.
3. Il **archive** le bruit (newsletters, notifications GitHub de PR/CI, codes déjà périmés).
4. Il **laisse dans la boîte** les mails humains, les factures, la sécurité, les invitations, les tickets ouverts.
5. S’il trouve au moins un mail **important**, il vous envoie un mail d’alerte à vous-même, sujet commençant par `[Alerte Gmail]`.
6. S’il n’y a rien d’important : **aucun mail**. Silence = journée calme.

Rien n’est mis à la corbeille. L’agent **ne répond jamais** à un tiers (ProtectedSeas, LangChain, Dileep, etc.) sauf si vous le demandez clairement.

## Qu’est-ce qu’un mail important ?

Un mail est important s’il reçoit `À répondre` (`Label_42`) ou `Action requise` (`Label_43`), ou s’il vient d’un humain du projet (ProtectedSeas, VLIZ, LangChain, équipe Berry-Mappemonde, support Nebius / Google / Toloka).

**Exception jusqu’au 5 octobre 2026 :** l’absence d’Alex Driedger (ProtectedSeas) n’est **pas** une alerte. On ne le relance pas avant son retour.

## Libellés (ne pas les recréer)

Gmail identifie les libellés par un numéro (`Label_10`, …), pas par le nom affiché. Toujours utiliser ces IDs.

| Famille | Exemples |
|---|---|
| Correspondants | GitHub `Label_10`, Nebius `11`, Cloudflare `12`, OVH `13`, Google `14`, Qonto `15`, HelloAsso `16`, ProtectedSeas `18`, Copernicus `20`, Cursor `21`, Toloka `23`, GitLab `24`, VLIZ `25`, Équipe `26`, Schoolmaker `27`, Newsletters `29`, Emergent `50`, MongoDB `51`, Anthropic `53`, AWS `54`, LangChain `55`, PaymentLabs `57` |
| Thèmes | Blue Intelligence `31`, NAVIGUIDE `32`, Hackathon `33`, Infra `34`, Factures `35`, Sécurité `36`, Association `37`, Formation `38`, Partenariats `39` |
| Pertinence | Projet actuel `41`, À répondre `42`, Action requise `43`, Info seulement `44` |
| GitHub | Pull requests `46`, CI `47`, Compte `48`, Invitations `49` |

Ne pas toucher aux vieux libellés YAMM, `LATOUR`, `H35 avocats`.

## Comment l’agent classe (MCP Gmail)

```
search_threads  query=newer_than:1d -in:draft   pageSize=50   (paginer)
search_threads  query=in:inbox has:nouserlabels
classer.py --from … --subject … --json
label_thread    threadId + labelIds
unlabel_thread  INBOX     uniquement si archive=true
```

- Un fil peut avoir **plusieurs** libellés.
- `create_filter` / `list_filters` renvoient **403** : ne pas relancer en boucle.
- Si un appel Gmail échoue : **un seul essai**, puis continuer.
- Classer d’après le **dernier message entrant** du fil, pas d’après un mail que vous avez envoyé.

Pour vérifier une règle sans toucher Gmail :

```bash
python3 scripts/gmail/classer.py \
  --from 'amada@langchain.dev' \
  --subject 'Re: Your LangSmith Credits'
python3 scripts/gmail/test_classer.py
```

## Contenu du mail d’alerte

Destinataire : la même boîte (un mail à vous-même).  
Sujet : `[Alerte Gmail] N mail(s) important(s) — JJ/MM`

Pour chaque fil important, une ligne simple :

- qui a écrit
- le sujet
- pourquoi c’est important
- le lien `https://mail.google.com/mail/u/0/#inbox/<threadId>`

Ne jamais coller de mot de passe, de code 2FA ou de clé API dans l’alerte.

## Filtres Gmail à créer à la main (Mac)

Les filtres automatiques via l’API sont bloqués. En attendant, vous pouvez en poser deux ou trois dans Gmail pour le bruit le plus fréquent.

1. Ouvrez [Gmail](https://mail.google.com) dans le navigateur.
2. Cliquez sur la roue dentée en haut à droite → **Voir tous les paramètres**.
3. Onglet **Filtres et adresses bloquées** → **Créer un filtre**.
4. Dans **De**, collez une adresse ci-dessous → **Créer un filtre**.
5. Cochez **Ignorer la boîte de réception (archiver)** et **Appliquer le libellé**, puis validez.

| De | Libellé | Archiver ? |
|---|---|---|
| `notifications@github.com` | `GitHub/Pull requests` | oui |
| `newsletter@` / `noreply@schoolmaker.co` | `Correspondants/Newsletters` | oui |
| `hello@qonto.com` | `Correspondants/Qonto` | oui (sauf relevé / virement) |

Les mails importants (humains, factures, sécurité) **ne doivent pas** être filtrés : l’agent du matin s’en occupe.

## Si le passage quotidien s’arrête

Le minuteur vit dans la conversation Cursor qui l’a créé. Il expire un jour. Si vous ne recevez plus d’alerte un matin où vous savez qu’un mail important est arrivé :

1. Rouvrez cette conversation d’agent, ou lancez un nouvel agent avec :  
   « Relance la surveillance Gmail quotidienne décrite dans `docs/gmail-surveillance-quotidienne.md`. »
2. L’agent doit relire `scripts/gmail/regles.json`, classer la journée, et **recréer le minuteur** `gmail-quotidien-berry` (`cron` `0 20 * * *`).

Les filtres manuels ci-dessus restent une sécurité même si l’agent dort.
