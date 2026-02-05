from flask import Flask, request, jsonify, send_from_directory, Response, send_file
from flask_cors import CORS
import json
import sys
import os
from ao3_scraper import scrape_ao3_history
from image_generator import generate_all_stat_images

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
    file_type = request.args.get('file', 'login')

    if file_type == 'item':
        debug_file = '/tmp/cc-agent/ao3_first_item_debug.html'
    else:
        debug_file = '/tmp/cc-agent/ao3_login_page_debug.html'

    if os.path.exists(debug_file):
        with open(debug_file, 'r', encoding='utf-8') as f:
            content = f.read()
        return jsonify({
            'found': True,
            'content': content,
            'length': len(content),
            'file': debug_file
        })
    return jsonify({'found': False, 'message': f'Debug file not found: {debug_file}'})


@app.route('/api/stats-image/<image_type>', methods=['GET'])
def get_stats_image(image_type):
    """Serve generated stat images"""
    image_files = {
        'ships': 'top_ships.png',
        'tags': 'top_tags.png',
        'fandoms': 'top_fandoms.png',
        'overall': 'overall_stats.png'
    }

    if image_type not in image_files:
        return jsonify({'error': 'Invalid image type'}), 400

    image_path = os.path.join('/tmp/ao3_stats', image_files[image_type])

    if not os.path.exists(image_path):
        return jsonify({'error': 'Image not found. Please run scraper first.'}), 404

    return send_file(image_path, mimetype='image/png')


def calculate_statistics(history_items):
    stats = {
        'totalFics': len(history_items),
        'totalWords': 0,
        'topTags': [],
        'topShips': [],
        'topFandoms': [],
        'longestFic': {
            'title': '',
            'wordCount': 0,
            'author': '',
            'url': ''
        }
    }

    tag_counts = {}
    ship_counts = {}
    fandom_counts = {}
    longest_fic = None

    for item in history_items:
        word_count = item.get('wordCount', 0)
        stats['totalWords'] += word_count

        # Track longest fic
        if word_count > stats['longestFic']['wordCount']:
            stats['longestFic'] = {
                'title': item.get('title', ''),
                'wordCount': word_count,
                'author': item.get('author', ''),
                'url': item.get('url', '')
            }

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
        progress_queue = []

        def on_progress(progress_data):
            progress_queue.append(progress_data)

        try:
            # Start scraping in a way that allows us to yield progress
            import threading
            import time

            scrape_result = {'items': None, 'error': None}

            def scrape_thread():
                try:
                    scrape_result['items'] = scrape_ao3_history(
                        username,
                        password,
                        year if year else None,
                        retries=3,
                        on_progress=on_progress
                    )
                except Exception as e:
                    scrape_result['error'] = e

            thread = threading.Thread(target=scrape_thread)
            thread.start()

            # Yield progress updates while scraping
            while thread.is_alive():
                while progress_queue:
                    progress_data = progress_queue.pop(0)
                    yield f'event: progress\ndata: {json.dumps(progress_data)}\n\n'
                time.sleep(0.5)

            # Yield any remaining progress updates
            while progress_queue:
                progress_data = progress_queue.pop(0)
                yield f'event: progress\ndata: {json.dumps(progress_data)}\n\n'

            # Check for errors
            if scrape_result['error']:
                raise scrape_result['error']

            history_items = scrape_result['items']
            print(f'Successfully scraped {len(history_items)} items')

            statistics = calculate_statistics(history_items)

            # Generate stat images
            print('Generating stat images...')
            try:
                image_paths = generate_all_stat_images(statistics)
                statistics['imagePaths'] = {
                    'ships': '/api/stats-image/ships',
                    'tags': '/api/stats-image/tags',
                    'fandoms': '/api/stats-image/fandoms',
                    'overall': '/api/stats-image/overall'
                }
                print('Stat images generated successfully')
            except Exception as img_error:
                print(f'Error generating images: {img_error}')
                statistics['imagePaths'] = {}

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

        # Generate stat images
        print('Generating stat images...')
        try:
            image_paths = generate_all_stat_images(statistics)
            statistics['imagePaths'] = {
                'ships': '/api/stats-image/ships',
                'tags': '/api/stats-image/tags',
                'fandoms': '/api/stats-image/fandoms',
                'overall': '/api/stats-image/overall'
            }
            print('Stat images generated successfully')
        except Exception as img_error:
            print(f'Error generating images: {img_error}')
            statistics['imagePaths'] = {}

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
