import httpx
import os
import json

RAILWAY_TOKEN = "2af86960-d485-495b-b845-f0574f0c452d"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {RAILWAY_TOKEN}"
}
URL = "https://backboard.railway.app/graphql/v2"

def run_query(query, variables=None):
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    r = httpx.post(URL, headers=HEADERS, json=payload)
    r.raise_for_status()
    data = r.json()
    if "errors" in data:
        raise Exception(f"GraphQL Error: {data['errors']}")
    return data["data"]

try:
    print("1. Creating Project...")
    q1 = '''
    mutation {
      projectCreate(input: {name: "Maritime Shorts Bot"}) {
        id
        environments { edges { node { id name } } }
      }
    }
    '''
    d1 = run_query(q1)
    project_id = d1["projectCreate"]["id"]
    env_id = d1["projectCreate"]["environments"]["edges"][0]["node"]["id"]
    print(f"   Project ID: {project_id}, Env ID: {env_id}")

    print("2. Creating Service...")
    q2 = '''
    mutation {
      serviceCreate(input: {
        projectId: "''' + project_id + '''",
        name: "Bot Worker",
        source: {
          repo: "meowzartai-dot/maritime-shorts"
        },
        branch: "main"
      }) { id name }
    }
    '''
    d2 = run_query(q2)
    service_id = d2["serviceCreate"]["id"]
    print(f"   Service ID: {service_id}")

    print("3. Updating Start Command & Nixpacks...")
    q3 = '''
    mutation {
      serviceInstanceUpdate(
        serviceId: "''' + service_id + '''",
        environmentId: "''' + env_id + '''",
        input: {
          startCommand: "python bot.py",
          restartPolicyType: ON_FAILURE,
          restartPolicyMaxRetries: 10
        }
      )
    }
    '''
    run_query(q3)
    
    import base64
    def b64_file(filename):
        with open(filename, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    # Environment variables are better handled via a separate ENV_VAR setup or os.environ
    env_vars = {
        "TELEGRAM_BOT_TOKEN": os.getenv("TELEGRAM_BOT_TOKEN"),
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
        "KIE_API_KEY": os.getenv("KIE_API_KEY"),
        "ADMIN_CHAT_ID": os.getenv("ADMIN_CHAT_ID"),
        "TZ": "America/New_York",
        "YOUTUBE_TOKEN_BASE64": b64_file("token.json"),
        "YOUTUBE_CLIENT_SECRETS_BASE64": b64_file("client_secrets.json")
    }
    
    q4 = '''
    mutation($projectId: String!, $environmentId: String!, $serviceId: String!, $variables: JSONObject!) {
      variableCollectionUpsert(input: {
        projectId: $projectId,
        environmentId: $environmentId,
        serviceId: $serviceId,
        variables: $variables
      })
    }
    '''
    run_query(q4, {
        "projectId": project_id,
        "environmentId": env_id,
        "serviceId": service_id,
        "variables": env_vars
    })
    
    print(f"Done! Dashboard: https://railway.app/project/{project_id}")

except Exception as e:
    print(f"Error: {e}")
