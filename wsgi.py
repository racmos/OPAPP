# wsgi.py
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env before app creation

from app import create_app  # noqa: E402

application = create_app()
