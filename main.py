import os
import json
import requests
from fastapi import FastAPI
from openai import OpenAI
from datetime import datetime

app = FastAPI()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
VENDASTA_API_KEY = os.getenv("VENDASTA_API_KEY", "")

def create_social_post(contact_id: str, topic: str, platform: str):
    try:
        url = "https://api.vendasta.com/social-ai/create"
        headers = {"Authorization": f"Bearer {VENDASTA_API_KEY}"}
        data = {"contact_id": contact_id, "topic": topic, "platforms": [platform]}
        res = requests.post(url, json=data, headers=headers, timeout=10)
        return res.json()
    except Exception as e:
        return {"status": "mock", "message": f"Post créé (mode test) : {topic} sur {platform}"}

def send_campaign(contact_id: str, type: str, content: str):
    try:
        url = "https://api.vendasta.com/campaigns-pro/send"
        headers = {"Authorization": f"Bearer {VENDASTA_API_KEY}"}
        data = {"contact_id": contact_id, "type": type, "content": content}
        res = requests.post(url, json=data, headers=headers, timeout=10)
        return res.json()
    except Exception as e:
        return {"status": "mock", "message": f"Campagne envoyée (mode test) : {type}"}

def save_to_crm(contact_id: str, note: str, agent: str):
    try:
        url = "https://api.vendasta.com/crm-ai/note"
        headers = {"Authorization": f"Bearer {VENDASTA_API_KEY}"}
        data = {"contact_id": contact_id, "note": f"[{agent}] {note}"}
        res = requests.post(url, json=data, headers=headers, timeout=10)
        return res.json()
    except Exception as e:
        return {"status": "mock", "message": f"Note sauvegardée (mode test) pour {contact_id}"}

tools = [
    {"type": "function", "function": {"name": "create_social_post", "description": "Crée un post social", "parameters": {"type": "object", "properties": {"contact_id": {"type": "string"}, "topic": {"type": "string"}, "platform": {"type": "string"}}, "required": ["contact_id", "topic", "platform"]}}},
    {"type": "function", "function": {"name": "send_campaign", "description": "Envoie une campagne", "parameters": {"type": "object", "properties": {"contact_id": {"type": "string"}, "type": {"type": "string"}, "content": {"type": "string"}}, "required": ["contact_id", "type", "content"]}}},
    {"type": "function", "function": {"name": "save_to_crm", "description": "Sauvegarde dans le CRM", "parameters": {"type": "object", "properties": {"contact_id": {"type": "string"}, "note": {"type": "string"}, "agent": {"type": "string"}}, "required": ["contact_id", "note", "agent"]}}}
]

AGENTS = {
    "FATIME": "Tu es FATIME, Responsable Marketing de TEAM FATIME. RÈGLES : Vouvoyez toujours le client. Ton professionnel et chaleureux. MISSION : Attirer des clients via create_social_post et send_campaign. Après chaque action, fais save_to_crm.",
    "ABRAHAM": "Tu es ABRAHAM, Responsable Commercial de TEAM FATIME. RÈGLES : Vouvoyez toujours le client. Ton sérieux. MISSION : Qualifier les leads. Pose 3 questions : Besoin, Budget, Délai. Après chaque échange, fais save_to_crm.",
    "AWA": "Tu es AWA, Responsable Support de TEAM FATIME. RÈGLES : Vouvoyez toujours le client. Ton chaleureux. MISSION : Fidéliser. J+2 demandez si tout va bien. J+3 demandez un avis Google. Après chaque échange, fais save_to_crm.",
    "SHEICKNER": "Tu es SHEICKNER, Directeur Général de TEAM FATIME. RÈGLES : Vouvoyez le client. Tu peux tutoyer les agents. MISSION : Superviser, analyser, produire des rapports. Après chaque rapport, fais save_to_crm."
}

TOOL_MAP = {
    "create_social_post": create_social_post,
    "send_campaign": send_campaign,
    "save_to_crm": save_to_crm
}

@app.get("/")
async def root():
    return {"status": "TEAM FATIME est en ligne ✅", "agents": list(AGENTS.keys()), "version": "1.0"}

@app.post("/chat/{agent_name}")
async def chat(agent_name: str, message: str, contact_id: str = "default"):
    if agent_name not in AGENTS:
        return {"error": f"Agent '{agent_name}' introuvable. Agents disponibles : {list(AGENTS.keys())}"}
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": AGENTS[agent_name]}, {"role": "user", "content": message}],
        tools=tools,
        tool_choice="auto"
    )
    reply = response.choices[0].message
    tool_results = []
    if reply.tool_calls:
        for tool_call in reply.tool_calls:
            fn_name = tool_call.function.name
            fn_args = json.loads(tool_call.function.arguments)
            if fn_name in TOOL_MAP:
                result = TOOL_MAP[fn_name](**fn_args)
                tool_results.append({"tool": fn_name, "result": result})
    return {"agent": agent_name, "reply": reply.content, "tools_called": tool_results}

@app.post("/boss/order")
async def boss_order(order: str, contact_id: str = "internal"):
    return await chat("SHEICKNER", order, contact_id)
