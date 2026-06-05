# sstats_client.py - клиент для SStats API
import requests
import json
import os
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict

class SStatsClient:
    def __init__(self, api_key: str, cache_dir: str = "/app/data/sstats_cache"):
        self.api_key = api_key
        self.base_url = "https://api.sstats.net"
        self.cache_dir = cache_dir
        self.tz = timezone(timedelta(hours=3))  # Московское время
        
        # Создаём папку для кэша
        os.makedirs(cache_dir, exist_ok=True)
    
    def _get_headers(self) -> Dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def _get_from_cache(self, key: str, ttl: int = 3600) -> Optional[Dict]:
        """Получает данные из кэша, если они не устарели"""
        cache_file = os.path.join(self.cache_dir, f"{key}.json")
        if os.path.exists(cache_file):
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached = json.load(f)
            if time.time() - cached.get('timestamp', 0) < ttl:
                return cached.get('data')
        return None
    
    def _save_to_cache(self, key: str, data: Any):
        """Сохраняет данные в кэш"""
        cache_file = os.path.join(self.cache_dir, f"{key}.json")
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump({'timestamp': time.time(), 'data': data}, f, ensure_ascii=False)
    
    def get_today_matches(self, limit: int = 50) -> List[Dict]:
        """Получает матчи на сегодня"""
        today = datetime.now(self.tz).strftime("%Y-%m-%d")
        cache_key = f"matches_{today}"
        
        # Пробуем получить из кэша (TTL 1 час)
        cached = self._get_from_cache(cache_key, ttl=3600)
        if cached:
            print(f"📦 Загружено из кэша: {len(cached)} матчей")
            return cached
        
        url = f"{self.base_url}/games/list"
        params = {
            "Date": today,
            "TimeZone": 3,
            "Limit": limit
        }
        
        try:
            response = requests.get(url, headers=self._get_headers(), params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                matches = data.get('data', [])
                self._save_to_cache(cache_key, matches)
                print(f"📡 Загружено из API: {len(matches)} матчей")
                return matches
            else:
                print(f"❌ Ошибка API: {response.status_code}")
                return []
        except Exception as e:
            print(f"❌ Ошибка запроса: {e}")
            return []
    
    
    # 2. Получить статистику ОБЕИХ команд для матча
    def get_match_stats(self, game_id: str, limit: int = 10) -> Dict:
        cache_key = f"match_stats_{game_id}_{limit}"
        cached = self._get_from_cache(cache_key, ttl=7200)
        if cached:
            return cached

        url = f"{self.base_url}/Games/last-games-stats"   #curl 'https://api.sstats.net/Games/last-games-stats?gameId=&limit=25&sameLeague=false&sameSeason=false&homeAway=false'
        params = {
            "gameId": game_id,
            "limit": limit,
            "sameLeague": "false",
            "sameSeason": "false",
            "homeAway": "false"
        }
        try:
            response = requests.get(url, headers=self._get_headers(), params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                self._save_to_cache(cache_key, data)
                return data
            else:
                print(f"❌ Ошибка получения статистики для {game_id}: {response.status_code}")
                return {}
        except Exception as e:
            print(f"❌ Ошибка запроса статистики: {e}")
            return {}
    
    def get_team_fixtures(self, team_id: int, limit: int = 10) -> List[Dict]:
        """Получает последние матчи команды"""
        cache_key = f"team_fixtures_{team_id}"
        
        cached = self._get_from_cache(cache_key, ttl=3600)
        if cached:
            return cached
        
        # Пробуем разные варианты эндпоинтов
        endpoints = [
            f"{self.base_url}/teams/{team_id}/fixtures",
            f"{self.base_url}/team/{team_id}/matches",
            f"{self.base_url}/fixtures/team/{team_id}",
        ]
        
        for url in endpoints:
            try:
                params = {"limit": limit} if limit else {}
                response = requests.get(url, headers=self._get_headers(), params=params, timeout=15)
                if response.status_code == 200:
                    data = response.json()
                    fixtures = data.get('data', []) if isinstance(data, dict) else data
                    self._save_to_cache(cache_key, fixtures)
                    return fixtures
            except:
                continue
        
        return []
    
    def search_team(self, query: str) -> List[Dict]:
        """Ищет команду по названию"""
        cache_key = f"search_{query.lower()}"
        
        cached = self._get_from_cache(cache_key, ttl=86400)  # 1 день
        if cached:
            return cached
        
        url = f"{self.base_url}/teams/search"
        params = {"q": query}
        
        try:
            response = requests.get(url, headers=self._get_headers(), params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                teams = data.get('data', []) if isinstance(data, dict) else data
                self._save_to_cache(cache_key, teams)
                return teams
            return []
        except:
            return []
    
    def get_h2h(self, team1_id: int, team2_id: int, limit: int = 5) -> List[Dict]:
        """Получает историю личных встреч"""
        cache_key = f"h2h_{team1_id}_{team2_id}"
        
        cached = self._get_from_cache(cache_key, ttl=86400)
        if cached:
            return cached
        
        endpoints = [
            f"{self.base_url}/fixtures/h2h",
            f"{self.base_url}/head2head",
        ]
        
        for url in endpoints:
            try:
                params = {"team1": team1_id, "team2": team2_id, "limit": limit}
                response = requests.get(url, headers=self._get_headers(), params=params, timeout=15)
                if response.status_code == 200:
                    data = response.json()
                    fixtures = data.get('data', []) if isinstance(data, dict) else data
                    self._save_to_cache(cache_key, fixtures)
                    return fixtures
            except:
                continue
        
        return []


# В конце файла, после основного кода
if __name__ == "__main__":
    API_KEY = os.getenv("API_KEY")  # ваш ключ
    
    client = SStatsClient(API_KEY)
    
    print("=" * 60)
    print("📊 ТЕСТИРОВАНИЕ SStats КЛИЕНТА")
    print("=" * 60)
    
    # Получаем матчи на сегодня
    matches = client.get_today_matches(limit=10)
    print(f"\n📋 МАТЧИ НА СЕГОДНЯ:")
    for i, match in enumerate(matches[:5], 1):
        home = match.get('homeTeam', {}).get('name', '?')
        away = match.get('awayTeam', {}).get('name', '?')
        game_id = match.get('id')
        print(f"  {i}. {home} vs {away} (ID: {game_id})")
    
    # Пробуем получить статистику для первого матча
    if matches:
        first_match = matches[0]
        game_id = first_match.get('id')
        home_team = first_match.get('homeTeam', {}).get('name', '?')
        away_team = first_match.get('awayTeam', {}).get('name', '?')
        
        print(f"\n📊 ПОЛУЧАЕМ СТАТИСТИКУ ДЛЯ МАТЧА: {home_team} vs {away_team}")
        print(f"🆔 Game ID: {game_id}")
        
        if game_id:
            stats = client.get_match_stats(game_id, limit=10)
            
            if stats:
                print(f"\n✅ СТАТИСТИКА ПОЛУЧЕНА:")
                print(f"📦 Структура ответа: {type(stats)}")
                print(f"🔑 Ключи: {list(stats.keys()) if isinstance(stats, dict) else 'не словарь'}")
                
                # Показываем первые 500 символов для понимания структуры
                import json
                print(f"\n📄 ПЕРВЫЕ 500 СИМВОЛОВ ОТВЕТА:")
                print(json.dumps(stats, ensure_ascii=False, indent=2)[:500])
            else:
                print("❌ Статистика не получена")
        else:
            print("❌ Нет game_id у матча")

