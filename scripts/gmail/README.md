# Classement Gmail Berry-Mappemonde

Règles : `regles.json`  
Moteur : `classer.py` (aucun appel réseau, aucun secret)  
Méthode complète : [`docs/gmail-surveillance-quotidienne.md`](../../docs/gmail-surveillance-quotidienne.md)

```bash
python3 scripts/gmail/test_classer.py
python3 scripts/gmail/classer.py --from 'amada@langchain.dev' --subject 'Re: Your LangSmith Credits'
```
