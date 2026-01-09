const axios = require('axios');
const cheerio = require('cheerio');
const tough = require('tough-cookie');
const { wrapper } = require('axios-cookiejar-support');

async function scrapeAO3History(username, password) {
  try {
    // Create cookie jar for session management
    const cookieJar = new tough.CookieJar();

    // Create axios instance with cookie jar support
    const client = wrapper(axios.create({
      jar: cookieJar,
      withCredentials: true,
      timeout: 30000,
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
      }
    }));

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
          'Content-Type': 'application/x-www-form-urlencoded',
          'Referer': 'https://archiveofourown.org/users/login',
          'Origin': 'https://archiveofourown.org'
        },
        maxRedirects: 5,
        validateStatus: function (status) {
          return status >= 200 && status < 400;
        }
      }
    );

    // Check if login was successful by looking for error messages
    const loginCheck = cheerio.load(loginResponse.data);
    const errorMessage = loginCheck('.error').text();
    if (errorMessage && (errorMessage.includes('password') || errorMessage.includes('couldn\'t find'))) {
      throw new Error('Invalid username or password');
    }

    // Add small delay to avoid rate limiting
    await new Promise(resolve => setTimeout(resolve, 1000));

    // Get history page
    const historyUrl = `https://archiveofourown.org/users/${username}/readings`;
    const historyResponse = await client.get(historyUrl, {
      headers: {
        'Referer': 'https://archiveofourown.org/'
      }
    });
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
    // Provide more specific error messages
    if (error.code === 'ECONNABORTED') {
      throw new Error('Request timed out. AO3 may be slow or unavailable.');
    }
    if (error.code === 'ECONNREFUSED') {
      throw new Error('Connection refused. AO3 may be down.');
    }
    if (error.code === 'ENOTFOUND') {
      throw new Error('Could not reach AO3. Please check your internet connection.');
    }
    if (error.message && error.message.includes('socket hang up')) {
      throw new Error('Connection interrupted. Please try again.');
    }
    if (error.response) {
      if (error.response.status === 429) {
        throw new Error('Rate limited by AO3. Please wait a few minutes and try again.');
      }
      throw new Error(`HTTP Error: ${error.response.status} - ${error.response.statusText}`);
    }
    throw error;
  }
}

module.exports = { scrapeAO3History };
