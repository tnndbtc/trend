import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# OpenAI API Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "YOUR_API_KEY")
MODEL = os.getenv("MODEL", "gpt-4o-mini")

# Trend Agent Configuration
MAX_TRENDS = int(os.getenv("MAX_TRENDS", "30"))
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")
