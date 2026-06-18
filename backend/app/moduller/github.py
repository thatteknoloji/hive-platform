import os

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

def get_github_token():
    return os.getenv("GITHUB_TOKEN", "")
