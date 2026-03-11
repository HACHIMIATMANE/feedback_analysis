"""
Royal Air Maroc - Feedback Intelligence API
Backend FastAPI connecté à Ollama (llama3.1)
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import json
import re
import logging
from typing import Optional

# ─── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ─── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="RAM Feedback Intelligence API",
    description="Analyse automatique des feedbacks passagers Royal Air Maroc via Ollama llama3.1",
    version="1.0.0"
)

# ─── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Config ────────────────────────────────────────────────────────────────────
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL    = "llama3.1"
REQUEST_TIMEOUT = 120  # secondes

# ─── Schémas Pydantic ──────────────────────────────────────────────────────────
class FeedbackRequest(BaseModel):
    text: str
    model: Optional[str] = OLLAMA_MODEL

class AnalysisResult(BaseModel):
    sentiment: str
    emotion: list[str]
    topics: list[str]
    customer_cluster: str
    urgency: str
    channel: str
    recommended_action: str
    impact: str
    language: str

class FeedbackResponse(BaseModel):
    success: bool
    analysis: Optional[AnalysisResult] = None
    raw_response: Optional[str] = None
    model_used: Optional[str] = None
    error: Optional[str] = None

# ─── Prompt Système ────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are an expert customer feedback analyst for Royal Air Maroc (RAM), a Moroccan airline.
Your task is to analyze passenger feedback/complaints and return a structured JSON analysis.

You MUST respond with ONLY a valid JSON object — no explanation, no markdown, no code block, no extra text.

Return exactly this JSON structure:
{
  "sentiment": "<Positif|Négatif|Neutre>",
  "emotion": ["<up to 3 from: Colère, Frustration, Déception, Satisfaction, Gratitude>"],
  "topics": ["<1-4 from: Retards, Bagages, Service client, Annulation, Remboursement, Personnel cabine, Nourriture, Confort, Ponctualité, Application/Site web>"],
  "customer_cluster": "<one of: Clients occasionnels très mécontents, Clients fréquents mais frustrés, Clients premium exigeants, Clients satisfaits fidèles, Nouveaux clients déçus>",
  "urgency": "<Faible|Moyenne|Élevée>",
  "channel": "<Email|Téléphone|Réseaux sociaux|Guichet|Application mobile|Site web|Non spécifié>",
  "recommended_action": "<one of: Remboursement immédiat, Compensation geste commercial, Suivi personnalisé, Réponse d'excuse, Escalade responsable, Investigation bagages>",
  "impact": "<one of: Expérience individuelle, Réputation compagnie, Fidélisation client, Impact légal potentiel>",
  "language": "<ISO 639-1 code: FR, EN, AR, ES, etc.>"
}

Rules:
- Detect language from the text content
- Infer channel from context clues (if mentioned)
- Urgency=Élevée if financial loss, safety, or very angry tone
- customer_cluster: infer from loyalty hints, tone, and context
- ONLY return the JSON object, nothing else"""

# ─── Helpers ───────────────────────────────────────────────────────────────────
def extract_json(text: str) -> dict:
    """Extrait le JSON depuis la réponse brute du LLM."""
    text = text.strip()

    # Supprimer les balises markdown éventuelles
    text = re.sub(r"```(?:json)?", "", text).strip()

    # Essayer parse direct
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Chercher un bloc JSON dans le texte
    match = re.search(r'\{[\s\S]*\}', text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Impossible d'extraire un JSON valide. Réponse reçue: {text[:300]}")


def validate_and_normalize(data: dict) -> dict:
    """Valide et normalise les champs du JSON retourné."""
    valid_sentiments = {"Positif", "Négatif", "Neutre"}
    valid_emotions   = {"Colère", "Frustration", "Déception", "Satisfaction", "Gratitude"}
    valid_urgency    = {"Faible", "Moyenne", "Élevée"}
    valid_clusters   = {
        "Clients occasionnels très mécontents",
        "Clients fréquents mais frustrés",
        "Clients premium exigeants",
        "Clients satisfaits fidèles",
        "Nouveaux clients déçus"
    }
    valid_channels = {
        "Email", "Téléphone", "Réseaux sociaux",
        "Guichet", "Application mobile", "Site web", "Non spécifié"
    }
    valid_actions = {
        "Remboursement immédiat", "Compensation geste commercial",
        "Suivi personnalisé", "Réponse d'excuse",
        "Escalade responsable", "Investigation bagages"
    }
    valid_impacts = {
        "Expérience individuelle", "Réputation compagnie",
        "Fidélisation client", "Impact légal potentiel"
    }

    # Normalisation des listes
    data["emotion"] = [e for e in data.get("emotion", []) if e in valid_emotions] or ["Frustration"]
    data["topics"]  = data.get("topics", ["Service client"])

    # Valeurs par défaut si invalides
    if data.get("sentiment") not in valid_sentiments:
        data["sentiment"] = "Neutre"
    if data.get("urgency") not in valid_urgency:
        data["urgency"] = "Moyenne"
    if data.get("customer_cluster") not in valid_clusters:
        data["customer_cluster"] = "Clients occasionnels très mécontents"
    if data.get("channel") not in valid_channels:
        data["channel"] = "Non spécifié"
    if data.get("recommended_action") not in valid_actions:
        data["recommended_action"] = "Suivi personnalisé"
    if data.get("impact") not in valid_impacts:
        data["impact"] = "Expérience individuelle"
    if not data.get("language"):
        data["language"] = "FR"

    return data


# ─── Routes ────────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "service": "RAM Feedback Intelligence API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Vérifie la connexion avec Ollama."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            if resp.status_code == 200:
                tags = resp.json()
                models = [m["name"] for m in tags.get("models", [])]
                llama_available = any(OLLAMA_MODEL in m for m in models)
                return {
                    "status": "healthy",
                    "ollama": "connected",
                    "available_models": models,
                    "llama3_1_ready": llama_available
                }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Ollama non accessible: {str(e)}. Assurez-vous qu'Ollama tourne sur localhost:11434"
        )


@app.post("/analyze", response_model=FeedbackResponse)
async def analyze_feedback(request: FeedbackRequest):
    """
    Analyse un feedback passager via Ollama llama3.1.
    
    - **text**: Le texte du feedback (obligatoire)
    - **model**: Modèle Ollama à utiliser (défaut: llama3.1)
    """
    if not request.text or len(request.text.strip()) < 5:
        raise HTTPException(status_code=400, detail="Le texte du feedback est trop court (minimum 5 caractères)")

    model = request.model or OLLAMA_MODEL
    logger.info(f"Analyse demandée | Modèle: {model} | Texte ({len(request.text)} chars)")

    # Construction du prompt
    user_prompt = f"""Analyse ce feedback passager Royal Air Maroc et retourne UNIQUEMENT le JSON:

\"\"\"{request.text.strip()}\"\"\""""

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_prompt}
        ],
        "stream": False,
        "options": {
            "temperature": 0.1,   # Très bas pour des résultats déterministes
            "top_p": 0.9,
            "num_predict": 512
        }
    }

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            logger.info(f"Envoi vers Ollama: {OLLAMA_BASE_URL}/api/chat")
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/chat",
                json=payload
            )
            response.raise_for_status()

    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail="Impossible de contacter Ollama. Vérifiez qu'Ollama est lancé: 'ollama serve'"
        )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail=f"Timeout après {REQUEST_TIMEOUT}s. Le modèle met trop de temps à répondre."
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Erreur Ollama: {e.response.text}"
        )

    # Parse de la réponse
    raw_data = response.json()
    raw_text = raw_data.get("message", {}).get("content", "")
    logger.info(f"Réponse brute Ollama: {raw_text[:200]}")

    try:
        parsed = extract_json(raw_text)
        validated = validate_and_normalize(parsed)
        analysis = AnalysisResult(**validated)

        logger.info(f"Analyse réussie | Sentiment: {analysis.sentiment} | Urgence: {analysis.urgency}")

        return FeedbackResponse(
            success=True,
            analysis=analysis,
            raw_response=raw_text,
            model_used=model
        )

    except (ValueError, KeyError, TypeError) as e:
        logger.error(f"Erreur de parsing: {e} | Réponse brute: {raw_text}")
        return FeedbackResponse(
            success=False,
            raw_response=raw_text,
            model_used=model,
            error=f"Erreur de parsing JSON: {str(e)}"
        )


@app.get("/models")
async def list_models():
    """Liste les modèles Ollama disponibles."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
