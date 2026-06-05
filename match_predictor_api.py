# match_predictor_api.py
import json
from collections import defaultdict
from sstats_client import SStatsClient

def calculate_btts_score(home_stats, away_stats):
    """Вероятность обеих забьют (0-10)"""
    # Средние голы за матч
    home_goals = home_stats.get('avgScore', 1.0)
    away_goals = away_stats.get('avgScore', 1.0)
    
    # Процент матчей, где команда забивала (оцениваем через avgScore)
    home_scored_prob = min(1.0, home_goals / 1.5) if home_goals else 0.5
    away_scored_prob = min(1.0, away_goals / 1.5) if away_goals else 0.5
    
    score = (home_scored_prob + away_scored_prob) * 5 + (home_goals + away_goals) / 2
    return min(10, round(score, 1))

def calculate_over25_score(home_stats, away_stats):
    """Вероятность тотала больше 2.5 (0-10)"""
    home_goals = home_stats.get('avgScore', 1.0)
    away_goals = away_stats.get('avgScore', 1.0)
    home_conceded = home_stats.get('avgConceded', 1.0)
    away_conceded = away_stats.get('avgConceded', 1.0)
    
    total_attack = home_goals + away_goals
    total_defense = home_conceded + away_conceded
    
    score = (total_attack + total_defense) / 1.5
    return min(10, round(score, 1))

def calculate_corners_score(home_stats, away_stats):
    """Вероятность тотала угловых > 8.5 (0-10)"""
    home_corners = home_stats.get('avgCorners', 4.0) or 4.0
    away_corners = away_stats.get('avgCorners', 4.0) or 4.0
    
    if home_corners == 0 or away_corners == 0:
        return 0
    
    score = (home_corners + away_corners) / 1.5
    return min(10, round(score, 1))

def calculate_yellow_score(home_stats, away_stats):
    """Вероятность тотала ЖК > 4.5 (0-10)"""
    home_yellow = home_stats.get('avgCards', 2.0) or 2.0
    away_yellow = away_stats.get('avgCards', 2.0) or 2.0
    
    if home_yellow == 0 or away_yellow == 0:
        return 0
    
    score = (home_yellow + away_yellow) * 1.5
    return min(10, round(score, 1))

def calculate_xg_score(home_stats, away_stats):
    """Оценка качества атаки по xG (0-10)"""
    home_xg = home_stats.get('avgOddsXg', 1.0) or 1.0
    away_xg = away_stats.get('avgOddsXg', 1.0) or 1.0
    
    score = (home_xg + away_xg) * 2
    return min(10, round(score, 1))

def analyze_match(match, stats):
    """Анализирует один матч и возвращает оценки"""
    home_stats = stats.get('home', {})
    away_stats = stats.get('away', {})
    
    return {
        'match': f"{match.get('homeTeam', {}).get('name')} vs {match.get('awayTeam', {}).get('name')}",
        'date': match.get('date', '—'),
        'home_form': f"{home_stats.get('wins', 0)}-{home_stats.get('draws', 0)}-{home_stats.get('losses', 0)}",
        'away_form': f"{away_stats.get('wins', 0)}-{away_stats.get('draws', 0)}-{away_stats.get('losses', 0)}",
        'home_goals': home_stats.get('avgScore', 0),
        'away_goals': away_stats.get('avgScore', 0),
        'home_corners': home_stats.get('avgCorners', 0),
        'away_corners': away_stats.get('avgCorners', 0),
        'home_yellow': home_stats.get('avgCards', 0),
        'away_yellow': away_stats.get('avgCards', 0),
        'btts_score': calculate_btts_score(home_stats, away_stats),
        'over25_score': calculate_over25_score(home_stats, away_stats),
        'corners_score': calculate_corners_score(home_stats, away_stats),
        'yellow_score': calculate_yellow_score(home_stats, away_stats),
        'xg_score': calculate_xg_score(home_stats, away_stats),
    }

def get_top_bets_api(client: SStatsClient, limit: int = 5):
    """Возвращает топ матчей для ставок через API"""
    matches = client.get_today_matches(limit=30)
    results = defaultdict(list)
    
    for match in matches[:20]:  # ограничиваем для скорости
        game_id = match.get('id')
        if not game_id:
            continue
        
        stats = client.get_match_stats(game_id, limit=10)
        if not stats or not stats.get('home'):
            continue
        
        match_info = analyze_match(match, stats)
        
        if match_info['btts_score'] >= 6:
            results['btts'].append(match_info)
        if match_info['over25_score'] >= 6:
            results['over25'].append(match_info)
        if match_info['corners_score'] >= 6:
            results['corners'].append(match_info)
        if match_info['yellow_score'] >= 6:
            results['yellow'].append(match_info)
        if match_info['xg_score'] >= 7:
            results['xg'].append(match_info)
    
    for key in results:
        results[key].sort(key=lambda x: x[f'{key}_score'], reverse=True)
        results[key] = results[key][:limit]
    
    return results

# Тестовый запуск
if __name__ == "__main__":
    from sstats_client import SStatsClient
    
    API_KEY = "g69egm3kibyrr20e"
    client = SStatsClient(API_KEY)
    
    print("🏆 ПОЛУЧАЕМ ЛУЧШИЕ СТАВКИ ЧЕРЕЗ API")
    print("=" * 60)
    
    top_bets = get_top_bets_api(client)
    
    for bet_type, matches in top_bets.items():
        print(f"\n📊 {bet_type.upper()}:")
        for match in matches[:3]:
            print(f"  • {match['match']} — {match.get(f'{bet_type}_score', 0)}/10")