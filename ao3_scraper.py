#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup
import json
import sys

def scrape_ao3_history(username, password):
    """
    Login to AO3 and scrape user's reading history
    """
    session = requests.Session()

    # Get login page to extract authenticity token
    login_url = "https://archiveofourown.org/users/login"
    response = session.get(login_url)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Extract CSRF token
    token = soup.find('input', {'name': 'authenticity_token'})['value']

    # Login
    login_data = {
        'user[login]': username,
        'user[password]': password,
        'authenticity_token': token
    }

    session.post('https://archiveofourown.org/users/login', data=login_data)

    # Get history page
    history_url = f"https://archiveofourown.org/users/{username}/readings"
    history_response = session.get(history_url)
    history_soup = BeautifulSoup(history_response.text, 'html.parser')

    # Parse history items
    history_items = []
    for item in history_soup.find_all('li', {'class': 'reading work blurb group'}):
        title_tag = item.find('h4', {'class': 'heading'})
        if title_tag:
            title = title_tag.get_text(strip=True)
            link = title_tag.find('a')['href']
            author_tag = item.find('a', {'rel': 'author'})
            author = author_tag.get_text(strip=True) if author_tag else 'Unknown'

            history_items.append({
                'title': title,
                'author': author,
                'url': f"https://archiveofourown.org{link}"
            })

    return history_items

if __name__ == "__main__":
    username = sys.argv[1]
    password = sys.argv[2]

    history = scrape_ao3_history(username, password)
    print(json.dumps(history))
