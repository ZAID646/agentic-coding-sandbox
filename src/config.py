import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ["OPENCODE_ZEN_API_KEY"]
BASE_URL = os.getenv("LLM_BASE_URL", "https://opencode.ai/zen/v1")
MODEL = os.getenv("LLM_MODEL", "deepseek-v4-flash-free")
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
SANDBOX_IMAGE = os.getenv("SANDBOX_IMAGE", "python:3.14-slim")
SANDBOX_TIMEOUT = int(os.getenv("SANDBOX_TIMEOUT", "30"))
