from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS
import json
import sys
from ao3_scraper import scrape_ao3_history

app = Flask(__name__, static_folder='public')
CORS(app)

print('Python version:', sys.version)
print('Flask and scraper loaded successfully')


@app.route('/')
def index():
    return send_from_directory('public', 'index.html')


@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'timestamp': str(__import__('datetime').datetime.now().isoformat())})


@app.route('/api/debug', methods=['GET'])
def debug():
    import os
    debug_file = '/tmp/ao3_login_page_debug.html'
    if os.path.exists(debug_file):
        with open(debug_file, 'r', encoding='utf-8') as f:
            content = f.read()
        return jsonify({
            'found': True,
            'content': content[:5000],
            'length': len(content)
        })
    return jsonify({'found': False})


def calculate_statistics(history_items):
    stats = {
        'totalFics': len(history_items),
        'totalWords': 0,
        'topTags': [],
        'topShips': [],
        'topFandoms': []
    }

    tag_counts = {}
    ship_counts = {}
    fandom_counts = {}

    for item in history_items:
        stats['totalWords'] += item.get('wordCount', 0)

        for tag in item.get('tags', []):
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

        for ship in item.get('relationships', []):
            ship_counts[ship] = ship_counts.get(ship, 0) + 1

        for fandom in item.get('fandoms', []):
            fandom_counts[fandom] = fandom_counts.get(fandom, 0) + 1

    # Sort and get top 10
    stats['topTags'] = [
        {'tag': tag, 'count': count}
        for tag, count in sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    ]

    stats['topShips'] = [
        {'ship': ship, 'count': count}
        for ship, count in sorted(ship_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    ]

    stats['topFandoms'] = [
        {'fandom': fandom, 'count': count}
        for fandom, count in sorted(fandom_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    ]

    return stats


@app.route('/api/scrape-stream', methods=['GET'])
def scrape_stream():
    username = request.args.get('username')
    password = request.args.get('password')
    year = request.args.get('year')

    if not username or not password:
        def error_generator():
            yield f'event: error\ndata: {json.dumps({"error": "Username and password required"})}\n\n'
        return Response(error_generator(), mimetype='text/event-stream')

    print(f'Starting scrape for user: {username}{f" (Year: {year})" if year else ""}')

    def generate():
        def on_progress(progress_data):
            yield f'event: progress\ndata: {json.dumps(progress_data)}\n\n'

        try:
            history_items = scrape_ao3_history(
                username,
                password,
                year if year else None,
                retries=3,
                on_progress=lambda data: None  # We'll handle progress differently
            )
            print(f'Successfully scraped {len(history_items)} items')

            statistics = calculate_statistics(history_items)

            yield f'event: complete\ndata: {json.dumps({"items": history_items, "statistics": statistics})}\n\n'
        except Exception as error:
            print('Scraping error:', str(error))
            yield f'event: error\ndata: {json.dumps({"error": str(error) or "Failed to scrape history"})}\n\n'

    return Response(generate(), mimetype='text/event-stream')


@app.route('/api/scrape', methods=['POST'])
def scrape():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    year = data.get('year')

    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400

    print(f'Starting scrape for user: {username}{f" (Year: {year})" if year else ""}')

    try:
        history_items = scrape_ao3_history(username, password, year if year else None)
        print(f'Successfully scraped {len(history_items)} items')

        statistics = calculate_statistics(history_items)

        return jsonify({
            'items': history_items,
            'statistics': statistics
        })
    except Exception as error:
        print('Scraping error:', str(error))
        return jsonify({
            'error': str(error) or 'Failed to scrape history. Please check your credentials.'
        }), 500


if __name__ == '__main__':
    port = int(__import__('os').environ.get('PORT', 3000))
    print(f'Server running on http://localhost:{port}')
    print(f'Health check available at: http://localhost:{port}/api/health')
    app.run(host='0.0.0.0', port=port, debug=False)
