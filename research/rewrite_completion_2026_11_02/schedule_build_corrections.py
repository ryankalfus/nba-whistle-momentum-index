"""One-run extraction of official NBA rendered game-title date evidence.

Saved evidence is web retrieval output, not original NBA HTTP bytes. The official
page title is retained verbatim; only the displayed date is normalized. Historical
metadata is never changed. This script refuses missing or conflicting evidence.
"""
import hashlib
import json
from pathlib import Path
import re
from datetime import datetime

raw = Path('output/v2/independent-schedule-2026-11-02')
report = json.loads(Path('research/rewrite_completion_2026_11_02/schedule_comparison_v3.json').read_text())
names = {'ATL': 'Atlanta Hawks', 'BOS': 'Boston Celtics', 'BKN': 'Brooklyn Nets', 'CHA': 'Charlotte Hornets', 'CHI': 'Chicago Bulls', 'CLE': 'Cleveland Cavaliers', 'DAL': 'Dallas Mavericks', 'DEN': 'Denver Nuggets', 'DET': 'Detroit Pistons', 'GSW': 'Golden State Warriors', 'HOU': 'Houston Rockets', 'IND': 'Indiana Pacers', 'LAC': 'LA Clippers', 'LAL': 'Los Angeles Lakers', 'MEM': 'Memphis Grizzlies', 'MIA': 'Miami Heat', 'MIL': 'Milwaukee Bucks', 'MIN': 'Minnesota Timberwolves', 'NOP': 'New Orleans Pelicans', 'NYK': 'New York Knicks', 'OKC': 'Oklahoma City Thunder', 'ORL': 'Orlando Magic', 'PHI': 'Philadelphia 76ers', 'PHX': 'Phoenix Suns', 'POR': 'Portland Trail Blazers', 'SAC': 'Sacramento Kings', 'SAS': 'San Antonio Spurs', 'TOR': 'Toronto Raptors', 'UTA': 'Utah Jazz', 'WAS': 'Washington Wizards'}
evidence = {}
for path in sorted(raw.glob('nba_web_*.txt')):
    content = path.read_bytes()
    for line in content.decode().splitlines():
        match = re.fullmatch(r'(.+?) vs (.+?) ([A-Z][a-z]{2} \d{1,2}, \d{4}) (?:Game Summary|Box Scores) \| NBA\.com \((https://www\.nba\.com/game/[^ ]+?(\d{10})(?:/box-score)?)\)', line)
        if match:
            away, home, date, url, game_id = match.groups()
            item = {'game_id': game_id, 'home_name': home, 'away_name': away, 'date': datetime.strptime(date, '%b %d, %Y').date().isoformat(), 'url': url, 'source_title': line.split(' (https:')[0], 'source_file': path.name, 'source_sha256': hashlib.sha256(content).hexdigest(), 'source_kind': 'web-tool-rendered-primary-NBA-page', 'date_basis': 'NBA displayed game date, corroborated against ESPN UTC converted to America/New_York; no NBA UTC timestamp acquired'}
            if game_id in evidence and evidence[game_id]['date'] != item['date']:
                raise ValueError('conflicting primary date evidence')
            evidence[game_id] = item
corrections = []
for row in report['unmatched_archive']:
    item = evidence[row['game_id']]
    assert (item['home_name'], item['away_name']) == (names[row['home']], names[row['away']])
    corrections.append({**item, 'historical_date': row['date'], 'home': row['home'], 'away': row['away'], 'reason': 'historical metadata date differs from official NBA displayed game date; original retained; corrected date independently corroborates ESPN completed event'})
with Path('research/rewrite_completion_2026_11_02/schedule_date_corrections.json').open('x') as stream:
    json.dump({'kind': 'official-NBA-rendered-date-corrections-v1', 'corrections': corrections}, stream, indent=2, sort_keys=True)
print(f'{len(corrections)} official primary NBA ID/team/date corrections')
