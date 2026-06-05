# config.py
# Конфигурация с классом для удобной работы с API

class SStatsConfig:
    """Конфигурация для SStats.net API"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.sstats.net"
        self.timezone = 3
        self.default_limit = 100
    
    def get_auth_params(self, params: dict = None) -> dict:
        """Возвращает параметры с добавленным API ключом"""
        if params is None:
            params = {}
        params["apikey"] = self.api_key
        return params
    
    @property
    def headers(self) -> dict:
        """Заголовки для запросов"""
        return {
            "User-Agent": "SStatsAPI/1.0",
            "Accept": "application/json"
        }


# ID популярных лиг
LEAGUES = {
    "premier_league": 39,
    "la_liga": 310,
    "serie_a": 183,
    "bundesliga": 41,
    "ligue_1": 56,
    "rfpl": 181
}

# Статусы матчей
GAME_STATUSES = {
    1: "Дата не объявлена",
    2: "Матч не начался",
    3: "Начало первого тайма",
    4: "Перерыв между таймами",
    5: "Начало второго тайма",
    6: "Дополнительное время",
    7: "Идёт серия пенальти",
    8: "Матч завершён",
    9: "Матч завершён после доп. времени",
    10: "Матч завершён после пенальти",
    11: "Перерыв в дополнительном времени",
    12: "Матч приостановлен",
    13: "Матч прерван",
    14: "Матч перенесён",
    15: "Матч отменён",
    17: "Техническое поражение",
    18: "Победа без игры",
    19: "Матч в процессе"
}