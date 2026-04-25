import httpx
import json
import base64
import os
from pathlib import Path

# --- Configuration ---
RAILWAY_TOKEN = "2af86960-d485-495b-b845-f0574f0c452d"
PROJECT_ID = "c034896a-ada5-43b7-9ad1-9464b2e937ac"
ENVIRONMENT_ID = "3651e474-288a-4c46-99e4-22782692e6c0"
SERVICE_ID = "c70bcbbc-b9b9-4605-86c2-140621d911a3"

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {RAILWAY_TOKEN}"
}
URL = "https://backboard.railway.app/graphql/v2"

def b64_file(filename):
    if os.path.exists(filename):
        with open(filename, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    return ""

def run_query(query, variables=None):
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    r = httpx.post(URL, headers=HEADERS, json=payload)
    if r.status_code != 200:
        print(f"Error {r.status_code}: {r.text}")
    r.raise_for_status()
    data = r.json()
    if "errors" in data:
        raise Exception(f"GraphQL Error: {data['errors']}")
    return data["data"]

# --- 1. Prepare Environment Variables ---
print("Preparing environment variables...")
env_vars = {
    "TELEGRAM_BOT_TOKEN": os.getenv("TELEGRAM_BOT_TOKEN"),
    "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
    "KIE_API_KEY": os.getenv("KIE_API_KEY"),
    "ADMIN_CHAT_ID": os.getenv("ADMIN_CHAT_ID"),
    "TZ": "America/New_York",
    "YOUTUBE_TOKEN_BASE64": b64_file("token.json"),
    "YOUTUBE_CLIENT_SECRETS_BASE64": b64_file("client_secrets.json")
}

# --- 2. Update Variables ---
print("Updating Railway variables...")
q_vars = """
mutation($projectId: String!, $environmentId: String!, $serviceId: String!, $variables: EnvironmentVariables!) {
  variableCollectionUpsert(input: {
    projectId: $projectId,
    environmentId: $environmentId,
    serviceId: $serviceId,
    variables: $variables
  })
}
"""
run_query(q_vars, {
    "projectId": PROJECT_ID,
    "environmentId": ENVIRONMENT_ID,
    "serviceId": SERVICE_ID,
    "variables": env_vars
})

# --- 3. Update Service Settings (Start Command) ---
print("Updating service settings...")
q_service = """
mutation($serviceId: String!, $environmentId: String!, $input: ServiceInstanceUpdateInput!) {
  serviceInstanceUpdate(serviceId: $serviceId, environmentId: $environmentId, input: $input)
}
"""
run_query(q_service, {
    "serviceId": SERVICE_ID,
    "environmentId": ENVIRONMENT_ID,
    "input": {
        "startCommand": "python bot.py",
        "restartPolicyType": "ON_FAILURE",
        "restartPolicyMaxRetries": 10
    }
})

# --- 4. Redeploy ---
print("Triggering redeploy...")
q_redeploy = """
mutation($serviceId: String!, $environmentId: String!) {
  serviceInstanceRedeploy(serviceId: $serviceId, environmentId: $environmentId)
}
"""
run_query(q_redeploy, {
    "serviceId": SERVICE_ID,
    "environmentId": ENVIRONMENT_ID
})

print("Deployment triggered successfully!")
print(f"Project Dashboard: https://railway.app/project/{PROJECT_ID}")
