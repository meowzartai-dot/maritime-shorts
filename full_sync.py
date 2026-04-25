import httpx
import json
import base64
import os

# --- Configuration ---
RAILWAY_TOKEN = "2af86960-d485-495b-b845-f0574f0c452d"
PROJECT_ID = "c034896a-ada5-43b7-9ad1-9464b2e937ac"
ENVIRONMENT_ID = "3651e474-288a-4c46-99e4-22782692e6c0"
SERVICE_ID = "c70bcbbc-b9b9-4605-86c2-140621d911a3"

HEADERS = {
    "Authorization": f"Bearer {RAILWAY_TOKEN}",
    "Content-Type": "application/json"
}
URL = "https://backboard.railway.app/graphql/v2"

def b64_file(filename):
    if os.path.exists(filename):
        with open(filename, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    return ""

def run_query(query, variables=None):
    payload = {"query": query, "variables": variables}
    r = httpx.post(URL, headers=HEADERS, json=payload)
    r.raise_for_status()
    return r.json()

# ALL VARIABLES IN ONE GO
env_vars = {
    "TELEGRAM_BOT_TOKEN": os.getenv("TELEGRAM_BOT_TOKEN"),
    "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
    "KIE_API_KEY": os.getenv("KIE_API_KEY"),
    "ADMIN_CHAT_ID": os.getenv("ADMIN_CHAT_ID"),
    "TZ": "America/New_York",
    "YOUTUBE_TOKEN_BASE64": b64_file("token.json"),
    "YOUTUBE_CLIENT_SECRETS_BASE64": b64_file("client_secrets.json")
}

print("Updating ALL variables at Environment level...")
q_vars = """
mutation($projectId: String!, $environmentId: String!, $variables: EnvironmentVariables!) {
  variableCollectionUpsert(input: {
    projectId: $projectId,
    environmentId: $environmentId,
    variables: $variables
  })
}
"""
run_query(q_vars, {"projectId": PROJECT_ID, "environmentId": ENVIRONMENT_ID, "variables": env_vars})

print("Final Variable Sync Complete!")
