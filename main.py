import json
import os
from datetime import datetime
from typing import Any

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from openai import OpenAI
from pydantic import BaseModel, Field

load_dotenv()

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
VENDASTA_API_KEY = os.getenv("VENDASTA_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

if not OPENAI_API_KEY:
    raise RuntimeError("La variable OPENAI_API_KEY est absente.")

client = OpenAI(api_key=OPENAI_API_KEY)

app = FastAPI(title="TEAM FATIME - Agence IA")


# Modèles des requêtes
class ChatRequest(BaseModel):
    message: str
    contact_id: str
    conversation_history: list[dict[str, Any]] = Field(default_factory=list)


class BossOrderRequest(BaseModel):
    order: str


# Fonction générique pour appeler Vendasta
def vendasta_post(endpoint: str, data: dict[str, Any]) -> dict[str, Any]:
    if not VENDASTA_API_KEY:
        return {
            "success": False,
            "error": "VENDASTA_API_KEY est absente."
        }

    headers = {
        "Authorization": f"Bearer {VENDASTA_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            endpoint,
            json=data,
            headers=headers,
            timeout=20,
        )

        response.raise_for_status()

        try:
            return response.json()
        except ValueError:
            return {
                "success": True,
                "status_code": response.status_code,
                "response": response.text,
            }

    except requests.RequestException as error:
        return {
            "success": False,
            "error": str(error),
            "note": "Vérifiez les endpoints et les identifiants API Vendasta.",
        }


# Outils TEAM FATIME
# Attention : ces URLs Vendasta doivent être confirmées avec leur documentation API.
def create_social_post(
    contact_id: str,
    topic: str,
    platform: str,
) -> dict[str, Any]:
    return vendasta_post(
        "https://api.vendasta.com/social-ai/create",
        {
            "contact_id": contact_id,
            "topic": topic,
            "platforms": [platform],
        },
    )


def send_campaign(
    contact_id: str,
    campaign_type: str,
    content: str,
) -> dict[str, Any]:
    return vendasta_post(
        "https://api.vendasta.com/campaigns-pro/send",
        {
            "contact_id": contact_id,
            "type": campaign_type,
            "content": content,
        },
    )


def save_to_crm(
    contact_id: str,
    note: str,
    agent: str,
) -> dict[str, Any]:
    return vendasta_post(
        "https://api.vendasta.com/crm-ai/note",
        {
            "contact_id": contact_id,
            "note": f"[{agent}] {note}",
        },
    )


# Outils visibles par le modèle
tools = [
    {
        "type": "function",
        "function": {
            "name": "create_social_post",
            "description": "Crée un brouillon de publication sur un réseau social.",
            "parameters": {
                "type": "object",
                "properties": {
                    "contact_id": {"type": "string"},
                    "topic": {"type": "string"},
                    "platform": {
                        "type": "string",
                        "enum": ["Instagram", "Facebook", "TikTok"],
                    },
                },
                "required": ["contact_id", "topic", "platform"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_campaign",
            "description": "Envoie une campagne par email ou SMS.",
            "parameters": {
                "type": "object",
                "properties": {
                    "contact_id": {"type": "string"},
                    "campaign_type": {
                        "type": "string",
                        "enum": ["email", "sms"],
                    },
                    "content": {"type": "string"},
                },
                "required": ["contact_id", "campaign_type", "content"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_to_crm",
            "description": "Enregistre une note dans le CRM.",
            "parameters": {
                "type": "object",
                "properties": {
                    "contact_id": {"type": "string"},
                    "note": {"type": "string"},
                    "agent": {"type": "string"},
                },
                "required": ["contact_id", "note", "agent"],
                "additionalProperties": False,
            },
        },
    },
]


# Prompts des agents
AGENTS = {
    "FATIME": """
Vous êtes FATIME, responsable marketing de TEAM FATIME.

Vous vouvoyez toujours le client.
Votre ton est professionnel, chaleureux et clair.
Vous créez des idées de publications et de campagnes marketing.

Règle importante :
Demandez la validation du client avant toute publication ou tout envoi réel.
Ne prétendez jamais qu'une action a été effectuée si l'outil a retourné une erreur.
Après une action, enregistrez un résumé dans le CRM.
""",
    "ABRAHAM": """
Vous êtes ABRAHAM, responsable commercial de TEAM FATIME.

Vous vouvoyez toujours le client.
Votre ton est sérieux, professionnel et orienté vers les besoins du client.
Pour qualifier une demande, posez les questions suivantes :
1. Quel est votre besoin ?
2. Quel budget avez-vous prévu ?
3. Dans quel délai souhaitez-vous avancer ?

Après chaque échange, enregistrez un résumé dans le CRM.
Ne promettez jamais de résultats garantis.
""",
    "AWA": """
Vous êtes AWA, responsable support et fidélité de TEAM FATIME.

Vous vouvoyez toujours le client.
Votre ton est patient, chaleureux et rassurant.
Vous écoutez le problème, proposez une réponse claire et indiquez les prochaines étapes.

Après chaque échange, enregistrez un résumé dans le CRM.
Ne prétendez jamais avoir effectué une action si elle n'est pas confirmée.
""",
    "SHEICKNER": """
Vous êtes SHEICKNER, directeur de TEAM FATIME.

Vous vouvoyez toujours les clients.
Votre ton est stratégique, professionnel et analytique.
Vous coordonnez les activités marketing, commerciales et support.
Vous ne présentez que des informations réellement disponibles.
Après chaque rapport, enregistrez un résumé dans le CRM.
""",
}


# Liste blanche : empêche l'exécution de fonctions non autorisées
AVAILABLE_FUNCTIONS = {
    "create_social_post": create_social_post,
    "send_campaign": send_campaign,
    "save_to_crm": save_to_crm,
}


def execute_tool(tool_name: str, arguments: str) -> dict[str, Any]:
    function = AVAILABLE_FUNCTIONS.get(tool_name)

    if function is None:
        return {"success": False, "error": "Outil non autorisé."}

    try:
        parsed_arguments = json.loads(arguments)
        return function(parsed_arguments)
    except (json.JSONDecodeError, TypeError, ValueError) as error:
        return {
            "success": False,
            "error": f"Arguments invalides : {error}",
        }
    except Exception as error:
        return {
            "success": False,
            "error": str(error),
        }


@app.get("/")
async def health_check():
    return {
        "status": "TEAM FATIME is online",
        "agents": list(AGENTS.keys()),
    }


@app.post("/chat/{agent_name}")
async def chat(agent_name: str, request: ChatRequest):
    if agent_name not in AGENTS:
        raise HTTPException(
            status_code=404,
            detail="Agent introuvable.",
        )

    messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": AGENTS[agent_name],
        }
    ]

    messages.extend(request.conversation_history)
    messages.append(
        {
            "role": "user",
            "content": request.message,
        }
    )

    first_response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=messages,
        tools=tools,
        tool_choice="auto",
        temperature=0.7,
    )

    assistant_message = first_response.choices[0].message

    if assistant_message.tool_calls:
        messages.append(
            assistant_message.model_dump(exclude_none=True)
        )

        for tool_call in assistant_message.tool_calls:
            result = execute_tool(
                tool_name=tool_call.function.name,
                arguments=tool_call.function.arguments,
            )

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(
                        result,
                        ensure_ascii=False,
                    ),
                }
            )

        second_response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            temperature=0.7,
        )

        final_reply = second_response.choices[0].message.content or ""
    else:
        final_reply = assistant_message.content or ""

    save_to_crm(
        contact_id=request.contact_id,
        note=(
            f"Message client : {request.message}\n"
            f"Réponse de {agent_name} : {final_reply}"
        ),
        agent=agent_name,
    )

    return {
        "agent": agent_name,
        "reply": final_reply,
        "contact_id": request.contact_id,
    }


@app.post("/boss/order")
async def boss_order(request: BossOrderRequest):
    routing_prompt = """
Vous êtes SHEICKNER, directeur de TEAM FATIME.

Choisissez l'agent le plus adapté à la demande.
Répondez uniquement avec un JSON valide sous cette forme :
{"agent": "FATIME", "task": "description"}

Agents disponibles :
- FATIME : marketing
- ABRAHAM : commercial
- AWA : support
"""

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {
                "role": "system",
                "content": routing_prompt,
            },
            {
                "role": "user",
                "content": request.order,
            },
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )

    try:
        decision = json.loads(
            response.choices[0].message.content or ""
        )
        selected_agent = decision["agent"]
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        raise HTTPException(
            status_code=500,
            detail=f"Réponse de routage invalide : {error}",
        )

    if selected_agent not in {"FATIME", "ABRAHAM", "AWA"}:
        raise HTTPException(
            status_code=400,
            detail="Agent sélectionné invalide.",
        )

    internal_request = ChatRequest(
        message=decision.get("task", request.order),
        contact_id="internal",
    )

    return await chat(selected_agent, internal_request)


@app.post("/sheickner/report")
async def generate_report(contact_id: str):
    """
    SHEICKNER génère un rapport hebdomadaire pour un client.
    """
    today = datetime.now()
    week_label = today.strftime("Semaine du %d %B %Y")

    mock_data = {
        "posts_created": 3,
        "campaigns_sent": 1,
        "leads_contacted": 12,
        "appointments_booked": 3,
        "reviews_collected": 5,
        "period": week_label,
    }

    report_prompt = f"""
Vous êtes SHEICKNER, directeur d
