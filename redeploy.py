import httpx
import json

token = '2af86960-d485-495b-b845-f0574f0c452d'
headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

query = """
mutation($serviceId: String!, $environmentId: String!) {
  serviceInstanceRedeploy(serviceId: $serviceId, environmentId: $environmentId)
}
"""

variables = {
    'serviceId': 'c70bcbbc-b9b9-4605-86c2-140621d911a3',
    'environmentId': '3651e474-288a-4c46-99e4-22782692e6c0'
}

r = httpx.post('https://backboard.railway.app/graphql/v2', headers=headers, json={'query': query, 'variables': variables})
print(json.dumps(r.json(), indent=2))
