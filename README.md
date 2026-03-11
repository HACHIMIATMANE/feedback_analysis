# Royal Air Maroc — Feedback Intelligence
> Analyse automatique des feedbacks passagers via **Ollama llama3.1** (100% local)



## Prérequis
# Installer les dépendances
pip install -r requirements.txt


| Outil | Version | Lien |
|---|---|---|
| Python | ≥ 3.11 | https://python.org |
| Ollama | latest | https://ollama.com |
| llama3.1 | 8B | `ollama pull llama3.1` |

---

## 🚀 Démarrage en 3 étapes

### Étape 1 — Installer et démarrer Ollama

# Télécharger le modèle llama3.1 (4.7 GB)
ollama pull llama3.1


### Étape 2 — Lancer le backend FastAPI

# Lancer le serveur (port 8000)
uvicorn main:app --reload 