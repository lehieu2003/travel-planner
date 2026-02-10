# backend/app/services/serpapi_service.py

import requests
from typing import Dict, Any, Optional
from app.core.config_loader import settings


class SerpAPIService:
    BASE_URL = "https://serpapi.com/search"

    def __init__(self):
        self.api_key = settings.SERPAPI_KEY

    def query(self, params: Dict[str, Any]) -> Dict[str, Any]:
        params["api_key"] = self.api_key

        try:
            response = requests.get(self.BASE_URL, params=params, timeout=20)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e), "raw": None}
