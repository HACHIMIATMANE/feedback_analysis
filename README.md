# 🛫 Royal Air Maroc — Feedback Intelligence
> Analyse automatique des feedbacks passagers via **Ollama llama3.1** (100% local)

---

## 📁 Structure du projet

```
ram-feedback-intelligence/
├── backend/
│   ├── main.py            ← API FastAPI
│   └── requirements.txt   ← Dépendances Python
├── frontend/
│   └── index.html         ← Interface web (ouvrir dans le navigateur)
└── README.md
```

---

## ⚙️ Prérequis

| Outil | Version | Lien |
|---|---|---|
| Python | ≥ 3.11 | https://python.org |
| Ollama | latest | https://ollama.com |
| llama3.1 | 8B | `ollama pull llama3.1` |

---

## 🚀 Démarrage en 3 étapes

### Étape 1 — Installer et démarrer Ollama

```bash
# Installer Ollama (macOS / Linux)
curl -fsSL https://ollama.com/install.sh | sh

# Windows : télécharger sur https://ollama.com/download

# Démarrer Ollama
ollama serve

# Télécharger le modèle llama3.1 (4.7 GB)
ollama pull llama3.1

# Vérifier que le modèle est disponible
ollama list
```

### Étape 2 — Lancer le backend FastAPI

```bash
# Se placer dans le dossier backend
cd backend

# Créer un environnement virtuel (recommandé)
python -m venv venv
source venv/bin/activate     # Linux/macOS
venv\Scripts\activate        # Windows

# Installer les dépendances
pip install -r requirements.txt

# Lancer le serveur (port 8000)
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

L'API sera accessible sur : **http://localhost:8000**
Documentation Swagger : **http://localhost:8000/docs**

### Étape 3 — Ouvrir le frontend

Ouvrir le fichier `frontend/index.html` directement dans votre navigateur.

> ⚠️ Assurez-vous que le backend tourne bien sur le port 8000 avant d'analyser.

---

## 🔌 Endpoints API

### `GET /health`
Vérifie la connexion Ollama et la disponibilité de llama3.1.

```json
{
  "status": "healthy",
  "ollama": "connected",
  "available_models": ["llama3.1:latest"],
  "llama3_1_ready": true
}
```

### `POST /analyze`
Analyse un feedback passager.

**Request:**
```json
{
  "text": "Mon vol a été annulé sans préavis...",
  "model": "llama3.1"
}
```

**Response:**
```json
{
  "success": true,
  "analysis": {
    "sentiment": "Négatif",
    "emotion": ["Colère", "Frustration"],
    "topics": ["Annulation", "Service client"],
    "customer_cluster": "Clients fréquents mais frustrés",
    "urgency": "Élevée",
    "channel": "Non spécifié",
    "recommended_action": "Remboursement immédiat",
    "impact": "Fidélisation client",
    "language": "FR"
  },
  "raw_response": "...",
  "model_used": "llama3.1"
}
```

### `GET /models`
Liste tous les modèles Ollama disponibles.

---

## 🧠 Champs analysés

| Champ | Valeurs possibles |
|---|---|
| `sentiment` | Positif · Négatif · Neutre |
| `emotion` | Colère · Frustration · Déception · Satisfaction · Gratitude |
| `topics` | Retards · Bagages · Service client · Annulation · Remboursement · Personnel cabine · Nourriture · Confort · Ponctualité · App/Site |
| `customer_cluster` | 5 segments clients |
| `urgency` | Faible · Moyenne · Élevée |
| `channel` | Email · Téléphone · Réseaux sociaux · Guichet · App mobile · Site web |
| `recommended_action` | 6 actions possibles |
| `impact` | 4 niveaux d'impact |
| `language` | Code ISO (FR, EN, AR, ES…) |

---

## 🐛 Dépannage

**"Ollama hors-ligne"**
→ Vérifiez que `ollama serve` tourne dans un terminal

**"llama3.1 manquant"**
→ Lancez `ollama pull llama3.1`

**Timeout lors de l'analyse**
→ Normal au premier appel (chargement du modèle en mémoire). Attendez ~30s.

**CORS Error dans le navigateur**
→ Vérifiez que le backend tourne bien sur `localhost:8000`

---

## 🔧 Configuration

Dans `backend/main.py`, vous pouvez modifier :
```python
OLLAMA_BASE_URL = "http://localhost:11434"  # URL Ollama
OLLAMA_MODEL    = "llama3.1"               # Modèle à utiliser
REQUEST_TIMEOUT = 120                       # Timeout en secondes
```

Pour utiliser un autre modèle (ex: mistral, llama3.2) :
```bash
ollama pull mistral
```
Puis changez `OLLAMA_MODEL = "mistral"` dans `main.py`.
