import base64
import os

def b64_file(filename):
    if os.path.exists(filename):
        with open(filename, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    return None

print(f"TOKEN_B64: {b64_file('token.json')}")
print(f"SECRETS_B64: {b64_file('client_secrets.json')}")
