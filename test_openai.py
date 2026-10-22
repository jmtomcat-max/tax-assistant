import os
import requests
import config

key = config.get_openai_api_key()
print(f"Key loaded: {'Yes' if key else 'No'}")
r = requests.get("https://api.openai.com/v1/models", headers={"Authorization": f"Bearer {key}"})
print(r.status_code)
print(r.text[:100])
