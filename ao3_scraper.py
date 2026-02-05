import requests
from bs4 import BeautifulSoup
import time
import random
from datetime import datetime


def delay(seconds):
    """Sleep for the specified number of seconds"""
    time.sleep(seconds)


def scrape_ao3_history(username, password, year=None, retries=3, on_progress=None):
    """
    Scrape AO3 reading history for a given user

    Args:
        username: AO3 username
        password: AO3 password
        year: Optional year to filter results (int or None)
        retries: Number of retry attempts
        on_progress: Optional callback function for progress updates

    Returns:
        List of history items
    """
    for attempt in range(1, retries + 1):
        try:
            print(f"Starting AO3 scraper (attempt {attempt}/{retries})...")

            # Create session for cookie management
            session = requests.Session()

            # Configure adapter with retry strategy for SSL errors
            from requests.adapters import HTTPAdapter
            from urllib3.util.retry import Retry

            # Create retry strategy
            retry_strategy = Retry(
                total=3,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504],
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            session.mount("https://", adapter)
            session.mount("http://", adapter)

            # More realistic browser headers to avoid detection
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Sec-Ch-Ua': '"Chromium";v="131", "Not_A Brand";v="24"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"Windows"',
                'Cache-Control': 'max-age=0',
                'DNT': '1'
            })

            # Small initial delay to appear more natural
            initial_delay = random.uniform(1, 2)
            print(f'Waiting {initial_delay:.1f} seconds before starting...')
            delay(initial_delay)

            # Get login page to extract authenticity token
            print('Fetching login page...')
            print('Making request to: https://archiveofourown.org/users/login')

            try:
                login_page_response = session.get(
                    'https://archiveofourown.org/users/login',
                    timeout=60
                )
                print('Login page response status:', login_page_response.status_code)

                if login_page_response.status_code == 429:
                    retry_after = login_page_response.headers.get('retry-after')
                    print('Rate limit detected (429)!')
                    print('Retry-After header:', retry_after)
                    raise Exception(f"AO3 returned 429 (Rate Limited). {f'Retry after {retry_after} seconds.' if retry_after else 'Please wait and try again later.'}")

                if login_page_response.status_code == 403:
                    print('403 Forbidden detected - possible bot detection')
                    raise Exception('AO3 returned 403 Forbidden. This may indicate bot detection or IP blocking. Try again later with a different connection.')

                if login_page_response.status_code == 503:
                    print('503 Service Unavailable - AO3 may be down')
                    raise Exception('AO3 is temporarily unavailable (503). Please try again later.')

                if login_page_response.status_code == 525:
                    print('525 SSL Handshake Failed')
                    raise Exception('SSL connection failed (525). This may be due to network issues or AO3\'s security settings. Try again in a few minutes or check your internet connection.')

                if login_page_response.status_code >= 400:
                    print(f'Unexpected status code: {login_page_response.status_code}')
                    raise Exception(f'AO3 returned error status {login_page_response.status_code}')

                login_page_response.raise_for_status()

            except requests.exceptions.RequestException as fetch_error:
                print('Failed to fetch login page:', str(fetch_error))
                raise

            # Verify response is properly decoded (not compressed)
            response_text = login_page_response.text
            if response_text and ord(response_text[0]) > 127:
                # Response appears to still be compressed
                print('WARNING: Response appears to be compressed. Content-Encoding:', login_page_response.headers.get('Content-Encoding'))
                raise Exception('Failed to decompress AO3 response. Try installing the brotli package.')

            # Parse login page to get authenticity token
            login_soup = BeautifulSoup(response_text, 'html.parser')

            # Debug: Check what page we actually got
            page_title = login_soup.find('title')
            if page_title:
                print('Login page title:', page_title.get_text(strip=True))

            # Debug: Look for the login form
            login_form = login_soup.find('form', {'id': 'new_user'})
            if not login_form:
                login_form = login_soup.find('form', {'action': '/users/login'})

            if login_form:
                print('Login form found')
            else:
                print('WARNING: Login form not found!')
                # Try to find any forms
                all_forms = login_soup.find_all('form')
                print(f'Found {len(all_forms)} form(s) on page')
                for i, form in enumerate(all_forms):
                    print(f'Form {i}: id={form.get("id")}, action={form.get("action")}')

            # Look for authenticity token - try multiple methods
            token_input = None
            token = None

            # Method 1: Look by name attribute
            token_input = login_soup.find('input', {'name': 'authenticity_token'})
            if token_input and token_input.get('value'):
                token = token_input['value']
                print('Found token via name attribute')

            # Method 2: Look by id attribute
            if not token:
                token_input = login_soup.find('input', {'id': 'authenticity_token'})
                if token_input and token_input.get('value'):
                    token = token_input['value']
                    print('Found token via id attribute')

            # Method 3: Look for any input with "token" in the name
            if not token:
                all_inputs = login_soup.find_all('input')
                for inp in all_inputs:
                    input_name = inp.get('name', '').lower()
                    if 'token' in input_name or 'csrf' in input_name:
                        if inp.get('value'):
                            token = inp['value']
                            print(f'Found token via input name: {inp.get("name")}')
                            break

            if not token:
                # Check if we got a CAPTCHA or error page
                captcha = login_soup.find('div', class_='g-recaptcha')
                if captcha:
                    raise Exception('AO3 is requiring CAPTCHA verification. This usually happens when too many requests are made. Please try again later or access AO3 directly in your browser first.')

                # Check for cloudflare or other blocking
                if 'cloudflare' in login_page_response.text.lower() or 'checking your browser' in login_page_response.text.lower():
                    raise Exception('AO3 is using anti-bot protection. Please try again in a few minutes.')

                # Check if AO3 is in maintenance mode
                if 'maintenance' in login_page_response.text.lower():
                    raise Exception('AO3 appears to be in maintenance mode. Please try again later.')

                # Generic error with detailed debugging
                print('=' * 50)
                print('ERROR: Could not find authenticity token')
                print('Response URL:', login_page_response.url)
                print('Response status:', login_page_response.status_code)
                print('Response headers:', dict(login_page_response.headers))
                print('Response length:', len(login_page_response.text))
                print('First 1000 chars of response:')
                print(login_page_response.text[:1000])
                print('=' * 50)

                # Save full response for debugging
                try:
                    import os
                    debug_dir = '/tmp/cc-agent'
                    os.makedirs(debug_dir, exist_ok=True)
                    debug_path = os.path.join(debug_dir, 'ao3_login_page_debug.html')
                    with open(debug_path, 'w', encoding='utf-8') as f:
                        f.write(response_text)
                    print(f'Full response saved to {debug_path}')
                except Exception as e:
                    print(f'Could not save debug file: {e}')

                raise Exception('Could not find authenticity token on login page. AO3 may be blocking automated access or their page structure has changed. Check logs for details.')

            print('Authenticity token found:', token[:20] + '...' if len(token) > 20 else token)

            # Add random delay before logging in (2-4 seconds)
            login_delay = random.uniform(2, 4)
            print(f'Waiting {login_delay:.1f} seconds before logging in...')
            delay(login_delay)

            # Prepare login data
            login_data = {
                'user[login]': username,
                'user[password]': password,
                'authenticity_token': token
            }

            # Login
            print('Attempting login...')
            login_response = session.post(
                'https://archiveofourown.org/users/login',
                data=login_data,
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Referer': 'https://archiveofourown.org/users/login',
                    'Origin': 'https://archiveofourown.org'
                },
                timeout=60
            )

            print('Login response received')
            print('Response status:', login_response.status_code)

            # Check if login was successful
            login_check_soup = BeautifulSoup(login_response.text, 'html.parser')
            error_element = login_check_soup.find(class_='error')

            if error_element:
                error_text = error_element.get_text(strip=True)
                if 'password' in error_text.lower() or "couldn't find" in error_text.lower():
                    raise Exception('Invalid username or password')

            # Verify we're logged in by checking for user-specific elements
            user_nav = login_check_soup.find(id='greeting')
            is_logged_in = user_nav is not None

            print('Login verification - user nav found:', is_logged_in)
            if user_nav:
                print('User greeting text:', user_nav.get_text(strip=True))

            if not is_logged_in:
                print('Login may have failed - no user navigation found')
                page_title = login_check_soup.find('title')
                if page_title:
                    print('Page title:', page_title.get_text(strip=True))

                # Try to find any error messages
                all_errors = login_check_soup.find_all(class_=['error', 'alert', 'notice'])
                if all_errors:
                    error_messages = [el.get_text(strip=True) for el in all_errors]
                    print('Found error messages:', error_messages)
                    raise Exception(f"Login failed: {', '.join(error_messages)}")

                print('No error messages found but login verification failed')

            print('Login successful')

            # Add random delay after login before fetching history (2-4 seconds)
            post_login_delay = random.uniform(2, 4)
            print(f'Waiting {post_login_delay:.1f} seconds after login...')
            delay(post_login_delay)

            # Fetch all pages of history with pagination
            history_items = []
            current_page = 1

            if on_progress:
                on_progress({
                    'currentPage': 0,
                    'totalItems': 0,
                    'status': 'Starting to fetch history pages...'
                })

            has_more_pages = True

            while has_more_pages:
                history_url = f'https://archiveofourown.org/users/{username}/readings?page={current_page}'
                print(f'Fetching reading history page {current_page}...')

                # Retry logic for individual page fetches
                page_fetch_attempts = 0
                max_page_attempts = 5  # Increased from 3
                history_response = None

                while page_fetch_attempts < max_page_attempts:
                    try:
                        history_response = session.get(
                            history_url,
                            headers={'Referer': 'https://archiveofourown.org/'},
                            timeout=60
                        )

                        # Check for error status codes
                        if history_response.status_code == 525:
                            print(f'525 SSL Handshake Failed on page {current_page}')
                            raise Exception('SSL connection failed (525)')

                        if history_response.status_code == 429:
                            retry_after = history_response.headers.get('retry-after', '60')
                            print(f'Rate limit detected (429) on page {current_page}')
                            raise Exception(f'Rate limited. Retry after {retry_after} seconds')

                        if history_response.status_code == 503:
                            print(f'503 Service Unavailable on page {current_page}')
                            raise Exception('AO3 temporarily unavailable (503)')

                        if history_response.status_code >= 400:
                            print(f'Unexpected status code {history_response.status_code} on page {current_page}')
                            raise Exception(f'HTTP error {history_response.status_code}')

                        history_response.raise_for_status()
                        print(f'History page {current_page} fetched successfully')
                        break  # Success, exit retry loop

                    except (requests.exceptions.SSLError, requests.exceptions.ConnectionError,
                            requests.exceptions.Timeout, Exception) as fetch_error:
                        page_fetch_attempts += 1
                        error_message = str(fetch_error)
                        print(f'Error fetching page {current_page} (attempt {page_fetch_attempts}/{max_page_attempts}): {error_message}')

                        if page_fetch_attempts >= max_page_attempts:
                            print(f'Failed to fetch page {current_page} after {max_page_attempts} attempts')
                            raise Exception(f'Could not fetch page {current_page} after {max_page_attempts} attempts: {error_message}')

                        # Longer waits for SSL errors (525)
                        if '525' in error_message or isinstance(fetch_error, requests.exceptions.SSLError):
                            retry_wait = 30 + (page_fetch_attempts * 30)  # 60s, 90s, 120s, 150s
                            print(f'SSL error detected - using extended cooldown period')

                            # Recreate session adapter to reset SSL connection state
                            if page_fetch_attempts >= 2:
                                print('Recreating session adapter to reset connection...')
                                retry_strategy = Retry(
                                    total=3,
                                    backoff_factor=1,
                                    status_forcelist=[429, 500, 502, 503, 504],
                                )
                                adapter = HTTPAdapter(max_retries=retry_strategy)
                                session.mount("https://", adapter)
                                session.mount("http://", adapter)
                        else:
                            retry_wait = page_fetch_attempts * 10  # 10s, 20s, 30s, 40s

                        print(f'Waiting {retry_wait} seconds before retrying page {current_page}...')
                        delay(retry_wait)

                if not history_response:
                    raise Exception(f'Failed to get response for page {current_page}')

                soup = BeautifulSoup(history_response.text, 'html.parser')

                # Debug: Log what we're seeing
                page_title = soup.find('title')
                if page_title:
                    print('Page title:', page_title.get_text(strip=True))

                # Try multiple selector patterns
                possible_selectors = [
                    'li.reading.work.blurb.group',
                    'ol.reading li.blurb',
                    'li.blurb.work',
                    'li.work.blurb'
                ]

                work_items = []
                working_selector = None

                for selector in possible_selectors:
                    if '.' in selector:
                        classes = selector.replace('li.', '').split('.')
                        if selector.startswith('ol.reading'):
                            ol = soup.find('ol', class_='reading')
                            if ol:
                                items = ol.find_all('li', class_='blurb')
                                work_items = items
                        else:
                            items = soup.find_all('li', class_=classes)
                            work_items = items
                    else:
                        work_items = soup.find_all(selector)

                    print(f'Trying selector "{selector}": found {len(work_items)} items')
                    if len(work_items) > 0:
                        working_selector = selector
                        break

                if not work_items:
                    print('No items found with any selector.')

                items_on_page = 0
                last_item_on_page = None

                # Debug: Save first item HTML on first page
                if current_page == 1 and len(work_items) > 0:
                    try:
                        import os
                        debug_dir = '/tmp/cc-agent'
                        os.makedirs(debug_dir, exist_ok=True)
                        debug_path = os.path.join(debug_dir, 'ao3_first_item_debug.html')
                        with open(debug_path, 'w', encoding='utf-8') as f:
                            f.write(str(work_items[0].prettify()))
                        print(f'First item HTML saved to {debug_path}')
                    except Exception as e:
                        print(f'Could not save first item debug: {e}')

                for item in work_items:
                    # Find the title link
                    title_element = item.find('h4', class_='heading')
                    if title_element:
                        title_link = title_element.find('a', href=lambda x: x and '/works/' in x)

                        if title_link:
                            title = title_link.get_text(strip=True)
                            link = title_link.get('href')

                            # Find author
                            author_element = item.find('a', rel='author')
                            author = author_element.get_text(strip=True) if author_element else 'Unknown'

                            # Extract word count
                            word_count = 0
                            stats_element = item.find('dd', class_='words')
                            if stats_element:
                                words_text = stats_element.get_text(strip=True).replace(',', '')
                                try:
                                    word_count = int(words_text)
                                except ValueError:
                                    word_count = 0

                            # Extract tags (separated by type)
                            tags = []  # Only freeform tags
                            relationships = []  # Ship tags
                            characters = []  # Character tags

                            relationship_elements = item.find_all('li', class_='relationships')
                            for rel_li in relationship_elements:
                                rel_tag = rel_li.find('a', class_='tag')
                                if rel_tag:
                                    relationship = rel_tag.get_text(strip=True)
                                    relationships.append(relationship)

                            character_elements = item.find_all('li', class_='characters')
                            for char_li in character_elements:
                                char_tag = char_li.find('a', class_='tag')
                                if char_tag:
                                    characters.append(char_tag.get_text(strip=True))

                            freeform_elements = item.find_all('li', class_='freeforms')
                            for free_li in freeform_elements:
                                free_tag = free_li.find('a', class_='tag')
                                if free_tag:
                                    tag_text = free_tag.get_text(strip=True)
                                    tags.append(tag_text)

                            if current_page == 1 and items_on_page == 0 and len(tags) > 0:
                                print(f'First item freeform tags: {tags}')

                            # Extract warnings
                            warnings = []
                            warning_elements = item.find_all('li', class_='warnings')
                            for warn_li in warning_elements:
                                warn_tag = warn_li.find('a', class_='tag')
                                if warn_tag:
                                    warnings.append(warn_tag.get_text(strip=True))

                            # Extract categories
                            categories = []
                            category_elements = item.find_all('li', class_='categories')
                            for cat_li in category_elements:
                                cat_tag = cat_li.find('a', class_='tag')
                                if cat_tag:
                                    categories.append(cat_tag.get_text(strip=True))

                            # Extract rating
                            rating_element = item.find('span', class_='rating')
                            if rating_element:
                                rating_text = rating_element.find('span', class_='text')
                                rating = rating_text.get_text(strip=True) if rating_text else 'Not Rated'
                            else:
                                rating = 'Not Rated'

                            # Extract fandoms
                            fandoms = []
                            fandom_heading = item.find('h5', class_='fandoms')
                            if fandom_heading:
                                fandom_links = fandom_heading.find_all('a', class_='tag')
                                fandoms = [f.get_text(strip=True) for f in fandom_links]

                            # Extract last visited date
                            last_visited = None
                            date_text = None
                            import re

                            # Try multiple approaches to find the date

                            # Approach 1: Look for h4.viewed with "Last visited:"
                            viewed_heading = item.find('h4', class_='viewed')
                            if viewed_heading:
                                full_heading_text = viewed_heading.get_text()
                                if 'Last visited:' in full_heading_text:
                                    date_match = re.search(r'(\d{1,2}\s+\w+\s+\d{4})', full_heading_text)
                                    if date_match:
                                        date_text = date_match.group(1)

                            # Approach 2: Look for span with datetime attribute
                            if not date_text:
                                datetime_span = item.find('span', {'datetime': True})
                                if datetime_span:
                                    date_text = datetime_span.get_text(strip=True)

                            # Approach 3: Look in any element with "Last visited" text
                            if not date_text:
                                all_text = item.get_text()
                                if 'Last visited:' in all_text:
                                    # Find text after "Last visited:"
                                    match = re.search(r'Last visited:\s*(\d{1,2}\s+\w+\s+\d{4})', all_text)
                                    if match:
                                        date_text = match.group(1)

                            # Approach 4: Look for dd element with date class
                            if not date_text:
                                date_dd = item.find('dd', class_='date')
                                if date_dd:
                                    date_text = date_dd.get_text(strip=True)

                            if date_text:
                                print(f'Found date text for "{title}": "{date_text}"')
                                try:
                                    # Try different date formats
                                    formats = ['%d %b %Y', '%d %B %Y', '%Y-%m-%d', '%b %d, %Y', '%B %d, %Y']
                                    for fmt in formats:
                                        try:
                                            last_visited = datetime.strptime(date_text, fmt)
                                            print(f'✓ Parsed date for "{title}": {last_visited.isoformat()} (Year: {last_visited.year})')
                                            break
                                        except ValueError:
                                            continue

                                    if not last_visited:
                                        print(f'✗ Could not parse date from text: "{date_text}" for "{title}"')
                                except Exception as e:
                                    print(f'✗ Error parsing date: {e}')
                            else:
                                print(f'✗ No "Last visited" date found for "{title}"')

                            if title and link:
                                work_item = {
                                    'title': title,
                                    'author': author,
                                    'url': f'https://archiveofourown.org{link}',
                                    'wordCount': word_count,
                                    'tags': tags,
                                    'characters': characters,
                                    'relationships': relationships,
                                    'warnings': warnings,
                                    'categories': categories,
                                    'rating': rating,
                                    'fandoms': fandoms,
                                    'lastVisited': last_visited.isoformat() if last_visited else None
                                }
                                history_items.append(work_item)

                                if last_visited:
                                    last_item_on_page = work_item

                                items_on_page += 1

                print(f'Found {items_on_page} items on page {current_page} (total: {len(history_items)})')

                if on_progress:
                    on_progress({
                        'currentPage': current_page,
                        'totalItems': len(history_items),
                        'status': f'Fetched page {current_page} - Found {len(history_items)} total items'
                    })

                # If filtering by year, check if we should stop
                if year and last_item_on_page and last_item_on_page.get('lastVisited'):
                    last_visited_dt = datetime.fromisoformat(last_item_on_page['lastVisited'])
                    last_item_year = last_visited_dt.year
                    target_year = int(year)
                    print(f'Year filter check - Last item on page: {last_item_year}, Target year: {target_year}')

                    if last_item_year < target_year:
                        print(f'\n========================================')
                        print(f'STOPPING: Last item on page {current_page} is from {last_item_year}, which is before target year {target_year}.')
                        print(f'All items from year {target_year} have been collected.')
                        print(f'========================================\n')
                        has_more_pages = False
                    else:
                        print(f'Last item year ({last_item_year}) is >= target year ({target_year}), continuing...')
                elif year:
                    print(f'Year filter enabled ({year}) but no valid dated item found on page {current_page}, continuing...')

                # Check if there's a next page
                if has_more_pages:
                    next_page_link = soup.find('ol', class_='pagination')
                    if next_page_link:
                        next_li = next_page_link.find('li', class_='next')
                        has_more_pages = next_li is not None and items_on_page > 0
                    else:
                        has_more_pages = False

                    if has_more_pages:
                        # Progressive delay that increases with page count
                        # Pages 1-10: 3-6 seconds
                        # Pages 11-20: 5-8 seconds
                        # Pages 21-30: 8-12 seconds
                        # Pages 31+: 12-18 seconds
                        if current_page <= 10:
                            random_delay = random.uniform(3, 6)
                        elif current_page <= 20:
                            random_delay = random.uniform(5, 8)
                        elif current_page <= 30:
                            random_delay = random.uniform(8, 12)
                        else:
                            random_delay = random.uniform(12, 18)

                        print(f'Waiting {random_delay:.1f} seconds before next page...')
                        delay(random_delay)

                        # Extended cooldown every 10 pages to avoid detection
                        if current_page % 10 == 0:
                            cooldown_time = 90  # 1.5 minutes
                            print(f'Completed {current_page} pages, extended cooldown of {cooldown_time} seconds to avoid rate limiting...')
                            delay(cooldown_time)
                        # Additional brief pause every 5 pages
                        elif current_page % 5 == 0:
                            print(f'Completed {current_page} pages, waiting 30 seconds...')
                            delay(30)

                        current_page += 1

            print(f'\nPagination stopped. Found {len(history_items)} total items across {current_page} pages')

            # Filter by year if specified
            filtered_items = history_items
            if year:
                filtered_items = [
                    item for item in history_items
                    if item.get('lastVisited') and
                    datetime.fromisoformat(item['lastVisited']).year == int(year)
                ]
                print(f'Filtered to {len(filtered_items)} items for year {year}')

            return filtered_items

        except Exception as error:
            print(f'Attempt {attempt}/{retries} failed: {str(error)}')

            # Check if this is a retryable error
            is_retryable = isinstance(error, (
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.SSLError
            ))

            # If it's the last attempt or not retryable, raise appropriate error
            if attempt == retries or not is_retryable:
                if 'Invalid username or password' in str(error):
                    raise error
                if isinstance(error, requests.exceptions.SSLError):
                    raise Exception('SSL connection error. This may be due to network issues, firewall settings, or AO3\'s security configuration. Try again in a few minutes or check your internet connection.')
                if isinstance(error, requests.exceptions.Timeout):
                    raise Exception('Request timed out. AO3 may be slow or unavailable. Try again in a few minutes.')
                if isinstance(error, requests.exceptions.ConnectionError):
                    raise Exception('Connection error. AO3 may be down or blocking requests.')
                raise error

            # Wait before retrying (exponential backoff)
            wait_time = attempt * 10
            print(f'Retrying in {wait_time} seconds...')
            delay(wait_time)

    raise Exception('All retry attempts failed')
