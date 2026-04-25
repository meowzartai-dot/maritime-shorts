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
    if r.status_code != 200:
        print(f"Error {r.status_code}: {r.text}")
    r.raise_for_status()
    return r.json()

# 1. Update Secrets at Environment Level
print("Updating Secrets at Environment level...")
env_secrets = {
    "YOUTUBE_TOKEN_BASE64": b64_file("token.json"),
    "YOUTUBE_CLIENT_SECRETS_BASE64": b64_file("client_secrets.json")
}
q_vars = """
mutation($projectId: String!, $environmentId: String!, $variables: EnvironmentVariables!) {
  variableCollectionUpsert(input: {
    projectId: $projectId,
    environmentId: $environmentId,
    variables: $variables
  })
}
"""
run_query(q_vars, {"projectId": PROJECT_ID, "environmentId": ENVIRONMENT_ID, "variables": env_secrets})

# 2. Update Start Command on Service
print("Updating Start Command...")
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
        "restartPolicyType": "ON_FAILURE"
    }
})

print("Done setting up Project 2!")
