import httpx
import json

# GitHub PAT from the remote URL
import os
token = os.getenv("GITHUB_TOKEN")
repo_name = "maritime-shorts"
headers = {
    "Authorization": f"token {token}",
    "Accept": "application/vnd.github.v3+json"
}

# 1. Check if repo exists
print(f"Checking if repo {repo_name} exists...")
r = httpx.get(f"https://api.github.com/user/repos", headers=headers)
if r.status_code == 200:
    repos = r.json()
    exists = any(repo["name"] == repo_name for repo in repos)
    if exists:
        print("Repo already exists. Checking visibility...")
        repo_data = next(repo for repo in repos if repo["name"] == repo_name)
        if repo_data["private"]:
            print("Repo is private. Updating to public...")
            r_patch = httpx.patch(repo_data["url"], headers=headers, json={"private": False})
            print("Update status:", r_patch.status_code)
        else:
            print("Repo is already public.")
    else:
        print("Repo does not exist. Creating public repo...")
        r_create = httpx.post("https://api.github.com/user/repos", headers=headers, json={
            "name": repo_name,
            "private": False,
            "description": "Maritime YouTube Shorts Automation Bot"
        })
        print("Creation status:", r_create.status_code)
        if r_create.status_code != 201:
            print("Error:", r_create.text)
else:
    print("Error fetching repos:", r.status_code, r.text)
