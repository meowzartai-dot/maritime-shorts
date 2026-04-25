import httpx
import json

token = '2af86960-d485-495b-b845-f0574f0c452d'
headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

query = """
{
  project(id: "c034896a-ada5-43b7-9ad1-9464b2e937ac") {
    name
    environments {
      edges {
        node {
          id
          name
          deployments(first: 5) {
            edges {
              node {
                id
                status
                staticUrl
                createdAt
              }
            }
          }
        }
      }
    }
    services {
      edges {
        node {
          id
          name
        }
      }
    }
  }
}
"""

r = httpx.post('https://backboard.railway.app/graphql/v2', headers=headers, json={'query': query})
print(json.dumps(r.json(), indent=2))
