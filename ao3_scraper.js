const axios = require('axios');
const cheerio = require('cheerio');

async function scrapeAO3History(username, password) {
  try {
    // Create axios instance with cookie jar
    const client = axios.create({
      withCredentials: true,
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
      }
    });

    // Get login page to extract authenticity token
    const loginPageResponse = await client.get('https://archiveofourown.org/users/login');
    const loginPage = cheerio.load(loginPageResponse.data);
    const token = loginPage('input[name="authenticity_token"]').val();

    if (!token) {
      throw new Error('Could not find authenticity token');
    }

    // Prepare login data
    const loginData = new URLSearchParams({
      'user[login]': username,
      'user[password]': password,
      'authenticity_token': token
    });

    // Login
    const loginResponse = await client.post(
      'https://archiveofourown.org/users/login',
      loginData.toString(),
      {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        },
        maxRedirects: 5
      }
    );

    // Check if login was successful by looking for error messages
    const loginCheck = cheerio.load(loginResponse.data);
    const errorMessage = loginCheck('.error').text();
    if (errorMessage && errorMessage.includes('password')) {
      throw new Error('Invalid username or password');
    }

    // Get history page
    const historyUrl = `https://archiveofourown.org/users/${username}/readings`;
    const historyResponse = await client.get(historyUrl);
    const $ = cheerio.load(historyResponse.data);

    // Parse history items
    const historyItems = [];
    $('li.reading.work.blurb.group').each((i, item) => {
      const $item = $(item);
      const titleElement = $item.find('h4.heading a.work');

      if (titleElement.length > 0) {
        const title = titleElement.first().text().trim();
        const link = titleElement.first().attr('href');
        const authorElement = $item.find('a[rel="author"]');
        const author = authorElement.length > 0 ? authorElement.first().text().trim() : 'Unknown';

        if (title && link) {
          historyItems.push({
            title,
            author,
            url: `https://archiveofourown.org${link}`
          });
        }
      }
    });

    return historyItems;
  } catch (error) {
    if (error.response) {
      throw new Error(`HTTP Error: ${error.response.status} - ${error.response.statusText}`);
    }
    throw error;
  }
}

module.exports = { scrapeAO3History };
