const axios = require('axios');
const cheerio = require('cheerio');
const tough = require('tough-cookie');
const { wrapper } = require('axios-cookiejar-support');
const https = require('https');

async function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function scrapeAO3History(username, password, retries = 3) {
  for (let attempt = 1; attempt <= retries; attempt++) {
    try {
      console.log(`Starting AO3 scraper (attempt ${attempt}/${retries})...`);

      // Create cookie jar for session management
      const cookieJar = new tough.CookieJar();

      // Create HTTPS agent with keep-alive
      const httpsAgent = new https.Agent({
        keepAlive: true,
        keepAliveMsecs: 1000,
        maxSockets: 50,
        maxFreeSockets: 10,
        timeout: 60000,
        rejectUnauthorized: true
      });

      // Create axios instance with cookie jar support
      const client = wrapper(axios.create({
        jar: cookieJar,
        withCredentials: true,
        timeout: 60000,
        httpsAgent: httpsAgent,
        maxRedirects: 5,
        headers: {
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
          'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
          'Accept-Language': 'en-US,en;q=0.9',
          'Accept-Encoding': 'gzip, deflate, br',
          'Connection': 'keep-alive',
          'Upgrade-Insecure-Requests': '1',
          'Sec-Fetch-Dest': 'document',
          'Sec-Fetch-Mode': 'navigate',
          'Sec-Fetch-Site': 'none'
        }
      }));

      // Get login page to extract authenticity token
      console.log('Fetching login page...');
      console.log('Making request to: https://archiveofourown.org/users/login');

      let loginPageResponse;
      try {
        loginPageResponse = await client.get('https://archiveofourown.org/users/login');
        console.log('Login page response status:', loginPageResponse.status);
        console.log('Login page response headers:', JSON.stringify(loginPageResponse.headers, null, 2));
      } catch (fetchError) {
        console.error('Failed to fetch login page:');
        console.error('Error code:', fetchError.code);
        console.error('Error message:', fetchError.message);
        console.error('Error stack:', fetchError.stack);
        throw fetchError;
      }

      const loginPage = cheerio.load(loginPageResponse.data);
      const token = loginPage('input[name="authenticity_token"]').val();
      console.log('Login page fetched successfully');

      if (!token) {
        throw new Error('Could not find authenticity token');
      }

      console.log('Authenticity token found');

      // Prepare login data
      const loginData = new URLSearchParams({
        'user[login]': username,
        'user[password]': password,
        'authenticity_token': token
      });

      // Add delay before login
      await delay(2000);

      // Login
      console.log('Attempting login...');
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

      console.log('Login response received');
      console.log('Response status:', loginResponse.status);

      // Check if login was successful by looking for error messages
      const loginCheck = cheerio.load(loginResponse.data);
      const errorMessage = loginCheck('.error').text();
      if (errorMessage && (errorMessage.includes('password') || errorMessage.includes('couldn\'t find'))) {
        throw new Error('Invalid username or password');
      }

      // Verify we're logged in by checking for user-specific elements
      const userNav = loginCheck('#greeting');
      const isLoggedIn = userNav.length > 0;

      console.log('Login verification - user nav found:', isLoggedIn);
      console.log('User greeting text:', userNav.text().trim());

      if (!isLoggedIn) {
        console.log('Login may have failed - no user navigation found');
        console.log('Page title:', loginCheck('title').text());

        // Try to find any error messages
        const allErrors = loginCheck('.error, .alert, .notice').map((i, el) => loginCheck(el).text().trim()).get();
        if (allErrors.length > 0) {
          console.log('Found error messages:', allErrors);
          throw new Error(`Login failed: ${allErrors.join(', ')}`);
        }

        // If no errors but also not logged in, something went wrong
        console.log('No error messages found but login verification failed');
      }

      console.log('Login successful');

      // Add delay to avoid rate limiting
      await delay(2000);

      // Get history page
      const historyUrl = `https://archiveofourown.org/users/${username}/readings`;
      console.log('Fetching reading history...');
      const historyResponse = await client.get(historyUrl, {
        headers: {
          'Referer': 'https://archiveofourown.org/'
        }
      });
      console.log('History page fetched successfully');
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

      console.log(`Found ${historyItems.length} items in reading history`);
      return historyItems;

    } catch (error) {
      console.error(`Attempt ${attempt}/${retries} failed:`, {
        message: error.message,
        code: error.code
      });

      // Check if this is a retryable error
      const isRetryable =
        error.code === 'ECONNRESET' ||
        error.code === 'ECONNABORTED' ||
        error.code === 'ETIMEDOUT' ||
        error.message.includes('socket hang up');

      // If it's the last attempt or not retryable, throw appropriate error
      if (attempt === retries || !isRetryable) {
        if (error.message === 'Invalid username or password') {
          throw error;
        }
        if (error.code === 'ECONNABORTED' || error.code === 'ETIMEDOUT') {
          throw new Error('Request timed out. AO3 may be slow or unavailable. Try again in a few minutes.');
        }
        if (error.code === 'ECONNREFUSED') {
          throw new Error('Connection refused. AO3 may be down or blocking requests.');
        }
        if (error.code === 'ENOTFOUND') {
          throw new Error('Could not reach AO3. Please check your internet connection.');
        }
        if (error.code === 'ECONNRESET' || error.message.includes('socket hang up')) {
          throw new Error('Connection was reset by AO3. This may indicate rate limiting or bot detection. Try again in a few minutes.');
        }
        if (error.response) {
          if (error.response.status === 429) {
            throw new Error('Rate limited by AO3. Please wait several minutes and try again.');
          }
          if (error.response.status === 503) {
            throw new Error('AO3 is temporarily unavailable. Please try again later.');
          }
          throw new Error(`HTTP Error: ${error.response.status} - ${error.response.statusText}`);
        }
        throw error;
      }

      // Wait before retrying (exponential backoff)
      const waitTime = attempt * 3000;
      console.log(`Retrying in ${waitTime/1000} seconds...`);
      await delay(waitTime);
    }
  }

  throw new Error('All retry attempts failed');
}

module.exports = { scrapeAO3History };
