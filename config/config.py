from dotenv import load_dotenv
import os

load_dotenv()

class Config:
    #DB password
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "5432"))
    DB_NAME = os.getenv("DB_NAME", "playground")
    DB_USER = os.getenv("DB_USER", "playground_user")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "playground_pass")

    #LLM (OpenAI-compatible local endpoint; e.g., Ollama)
    LLM_API_BASE = os.getenv("LLM_API_BASE", "http://localhost:11434/v1")
    LLM_API_KEY  = os.getenv("LLM_API_KEY", "ollama")
    LLM_MODEL    = os.getenv("LLM_MODEL", "gemma2:9b")

    #files
    QUESTIONS_PATH = os.getenv("QUESTIONS_PATH", "questions/questions.yaml")
    SOLUTIONS_PATH = os.getenv("SOLUTIONS_PATH", "solutions/solutions.yaml")

config = Config()
