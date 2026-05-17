import os
from dotenv import load_dotenv

load_dotenv()

KAKAO_API_KEY = os.getenv("KAKAO_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

RADIUS_PRIMARY = 500
RADIUS_SECONDARY = 1000
RADIUS_TERTIARY = 2000

DB_PATH = "database/gen_city.db"
