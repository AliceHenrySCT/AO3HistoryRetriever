import axios from 'axios';
import * as cheerio from 'cheerio';
import * as tough from 'tough-cookie';
import { wrapper } from 'axios-cookiejar-support';

async function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function scrapeAO3History(username, password, year = null, retries = 3, onProgress = null) {
  for (let attempt = 1; attempt <= retries; attempt++) {
    try {
      console.log(`Starting AO3 scraper (attempt ${attempt}/${retries})...`);

      // Create cookie jar for session management
      const cookieJar = new tough.CookieJar();

      // Create axios instance with cookie jar support (no custom agent)
      const client = wrapper(axios.create({
        jar: cookieJar,
        withCredentials: true,
        timeout: 60000,
        maxRedirects: 5,
        validateStatus: function (status) {
          return status >= 200 && status < 600;
        },
        headers: {
          'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
          'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
          'Accept-Language': 'en-US,en;q=0.9',
          'Accept-Encoding': 'gzip, deflate, br',
          'Connection': 'keep-alive',
          'Upgrade-Insecure-Requests': '1'
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

        if (loginPageResponse.status === 429) {
          const retryAfter = loginPageResponse.headers['retry-after'];
          const cfRay = loginPageResponse.headers['cf-ray'];
          console.error('Rate limit detected (429)!');
          console.error('Retry-After header:', retryAfter);
          console.error('CF-Ray:', cfRay);
          console.error('Response body (first 500 chars):',
            typeof loginPageResponse.data === 'string'
              ? loginPageResponse.data.substring(0, 500)
              : JSON.stringify(loginPageResponse.data).substring(0, 500)
          );
          throw new Error(`AO3 returned 429 (Rate Limited). ${retryAfter ? `Retry after ${retryAfter} seconds.` : 'Please wait and try again later.'}`);
        }

        if (loginPageResponse.status === 403) {
          console.error('403 Forbidden detected - possible bot detection');
          console.error('Response body (first 500 chars):',
            typeof loginPageResponse.data === 'string'
              ? loginPageResponse.data.substring(0, 500)
              : JSON.stringify(loginPageResponse.data).substring(0, 500)
          );
          throw new Error('AO3 returned 403 Forbidden. This may indicate bot detection or IP blocking. Try again later with a different connection.');
        }

        if (loginPageResponse.status === 503) {
          console.error('503 Service Unavailable - AO3 may be down');
          throw new Error('AO3 is temporarily unavailable (503). Please try again later.');
        }

        if (loginPageResponse.status >= 400) {
          console.error(`Unexpected status code: ${loginPageResponse.status}`);
          console.error('Response body (first 500 chars):',
            typeof loginPageResponse.data === 'string'
              ? loginPageResponse.data.substring(0, 500)
              : JSON.stringify(loginPageResponse.data).substring(0, 500)
          );
          throw new Error(`AO3 returned error status ${loginPageResponse.status}`);
        }

      } catch (fetchError) {
        console.error('Failed to fetch login page:');
        console.error('Error code:', fetchError.code);
        console.error('Error message:', fetchError.message);

        if (fetchError.response) {
          console.error('Response status:', fetchError.response.status);
          console.error('Response statusText:', fetchError.response.statusText);
          console.error('Response headers:', JSON.stringify(fetchError.response.headers, null, 2));
          console.error('Response data (first 500 chars):',
            typeof fetchError.response.data === 'string'
              ? fetchError.response.data.substring(0, 500)
              : JSON.stringify(fetchError.response.data).substring(0, 500)
          );
        } else if (fetchError.request) {
          console.error('Request was made but no response received');
          console.error('Request headers:', JSON.stringify(fetchError.config?.headers, null, 2));
        } else {
          console.error('Error setting up request:', fetchError.message);
        }

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

      // Fetch all pages of history with pagination
      const historyItems = [];
      let currentPage = 1;

      if (onProgress) {
        onProgress({
          currentPage: 0,
          totalItems: 0,
          status: 'Starting to fetch history pages...'
        });
      }
      let hasMorePages = true;

      while (hasMorePages) {
        const historyUrl = `https://archiveofourown.org/users/${username}/readings?page=${currentPage}`;
        console.log(`Fetching reading history page ${currentPage}...`);

        const historyResponse = await client.get(historyUrl, {
          headers: {
            'Referer': 'https://archiveofourown.org/'
          }
        });
        console.log(`History page ${currentPage} fetched successfully`);
        const $ = cheerio.load(historyResponse.data);

        // Debug: Log what we're actually seeing
        console.log('Page title:', $('title').text());
        console.log('Total li.reading elements:', $('li.reading').length);
        console.log('Total li.work elements:', $('li.work').length);
        console.log('Total li.blurb elements:', $('li.blurb').length);
        console.log('Total li.reading.work.blurb.group elements:', $('li.reading.work.blurb.group').length);

        // Try alternative selectors
        console.log('Total ol.reading li.blurb elements:', $('ol.reading li.blurb').length);
        console.log('Total li.blurb.work elements:', $('li.blurb.work').length);

        // Parse history items on this page
        let itemsOnPage = 0;
        // Track the last item with a valid date on this page (reset for each page)
        let lastItemOnPage = null;
        // Try multiple selector patterns
        const possibleSelectors = [
          'li.reading.work.blurb.group',
          'ol.reading li.blurb',
          'li.blurb.work',
          'li.work.blurb'
        ];

        let workingSelector = null;
        for (const selector of possibleSelectors) {
          const count = $(selector).length;
          console.log(`Trying selector "${selector}": found ${count} items`);
          if (count > 0 && !workingSelector) {
            workingSelector = selector;
          }
        }

        if (!workingSelector) {
          console.log('No items found with any selector. Logging page structure...');
          console.log('First 2000 chars of page:', historyResponse.data.substring(0, 2000));
        }

        const selectorToUse = workingSelector || 'li.reading.work.blurb.group';
        console.log(`Using selector: ${selectorToUse}`);

        $(selectorToUse).each((i, item) => {
          const $item = $(item);

          // Debug: Log the HTML of the first item to see the structure
          if (i === 0 && currentPage === 1) {
            console.log('\n=== DEBUG: First work item HTML structure ===');
            console.log($item.html().substring(0, 1500));
            console.log('=== END DEBUG ===\n');
          }

          // Find the title link - it's the first anchor in h4.heading that links to /works/
          const titleElement = $item.find('h4.heading a[href*="/works/"]').first();

          if (titleElement.length > 0) {
            const title = titleElement.first().text().trim();
            const link = titleElement.first().attr('href');
            const authorElement = $item.find('a[rel="author"]');
            const author = authorElement.length > 0 ? authorElement.first().text().trim() : 'Unknown';

            // Extract word count
            let wordCount = 0;
            const statsElement = $item.find('dd.words');
            if (statsElement.length > 0) {
              const wordsText = statsElement.text().trim().replace(/,/g, '');
              wordCount = parseInt(wordsText) || 0;
            }

            // Extract tags (relationships/ships, characters, freeform tags)
            const tags = [];
            const relationships = [];

            $item.find('li.relationships a.tag').each((i, el) => {
              const relationship = $(el).text().trim();
              relationships.push(relationship);
              tags.push(relationship);
            });

            $item.find('li.characters a.tag').each((i, el) => {
              tags.push($(el).text().trim());
            });

            $item.find('li.freeforms a.tag').each((i, el) => {
              tags.push($(el).text().trim());
            });

            // Extract rating
            const ratingElement = $item.find('span.rating span.text');
            const rating = ratingElement.length > 0 ? ratingElement.text().trim() : 'Not Rated';

            // Extract fandom
            const fandoms = [];
            $item.find('h5.fandoms a.tag').each((i, el) => {
              fandoms.push($(el).text().trim());
            });

            // Extract last visited date - look for text after "Last visited:" in h4.viewed.heading
            let lastVisited = null;
            let dateText = null;

            // Find h4.viewed.heading or h4.heading containing "Last visited:"
            const viewedHeading = $item.find('h4.viewed.heading, h4.heading:contains("Last visited:")').first();

            if (viewedHeading.length > 0) {
              const fullHeadingText = viewedHeading.text();

              // Check if this heading contains "Last visited:"
              if (fullHeadingText.includes('Last visited:')) {
                // Extract the date text that comes after "Last visited:"
                // Remove the span content and extract the remaining text
                const span = viewedHeading.find('span').first();
                if (span.length > 0) {
                  // Get all text after the span
                  const textAfterSpan = fullHeadingText.replace(span.text(), '').trim();
                  // Extract just the date part (before any parentheses or additional text)
                  const dateMatch = textAfterSpan.match(/^\s*(\d{1,2}\s+\w+\s+\d{4})/);
                  if (dateMatch) {
                    dateText = dateMatch[1];
                    console.log(`Found "Last visited" date for "${title}": "${dateText}"`);
                  }
                }
              }
            }

            if (dateText) {
              // Try multiple date pattern matches
              const patterns = [
                /\((\d{1,2}\s+\w+\s+\d{4})\)/,  // (14 Jan 2024)
                /(\d{1,2}\s+\w+\s+\d{4})/,      // 14 Jan 2024
              ];

              for (const pattern of patterns) {
                const dateMatch = dateText.match(pattern);
                if (dateMatch) {
                  lastVisited = new Date(dateMatch[1]);
                  console.log(`✓ Parsed date for "${title}": ${lastVisited.toISOString()} (Year: ${lastVisited.getFullYear()})`);
                  break;
                }
              }

              if (!lastVisited) {
                console.log(`✗ Could not parse date from text: "${dateText}" for "${title}"`);
              }
            } else {
              console.log(`✗ No "Last visited" date found for "${title}"`);
            }

            if (title && link) {
              const workItem = {
                title,
                author,
                url: `https://archiveofourown.org${link}`,
                wordCount,
                tags,
                relationships,
                rating,
                fandoms,
                lastVisited
              };
              historyItems.push(workItem);
              // Only update lastItemOnPage if this item has a valid date
              if (lastVisited) {
                lastItemOnPage = workItem;
              }
              itemsOnPage++;
            }
          }
        });

        console.log(`Found ${itemsOnPage} items on page ${currentPage} (total: ${historyItems.length})`);

        if (onProgress) {
          onProgress({
            currentPage,
            totalItems: historyItems.length,
            status: `Fetched page ${currentPage} - Found ${historyItems.length} total items`
          });
        }

        // If filtering by year, check if the last item on this page is before the target year
        // If so, we can stop scraping as all subsequent pages will be older
        if (year && lastItemOnPage && lastItemOnPage.lastVisited) {
          const lastItemYear = lastItemOnPage.lastVisited.getFullYear();
          const targetYear = parseInt(year);
          console.log(`Year filter check - Last item on page: ${lastItemYear}, Target year: ${targetYear}, Last item title: "${lastItemOnPage.title}"`);
          if (lastItemYear < targetYear) {
            console.log(`\n========================================`);
            console.log(`STOPPING: Last item on page ${currentPage} is from ${lastItemYear}, which is before target year ${targetYear}.`);
            console.log(`All items from year ${targetYear} have been collected.`);
            console.log(`========================================\n`);
            hasMorePages = false;
          } else {
            console.log(`Last item year (${lastItemYear}) is >= target year (${targetYear}), continuing...`);
          }
        } else if (year) {
          console.log(`Year filter enabled (${year}) but no valid dated item found on page ${currentPage}, continuing...`);
        }

        // Check if there's a next page (only if we haven't already decided to stop)
        if (hasMorePages) {
          const nextPageLink = $('ol.pagination li.next a').attr('href');
          hasMorePages = !!nextPageLink && itemsOnPage > 0;

          if (hasMorePages) {
            // Add 1 minute delay after every 5th page (only if continuing)
            if (currentPage % 5 === 0) {
              console.log(`Completed ${currentPage} pages, waiting 60 seconds to avoid rate limiting...`);
              await delay(60000);
            }
            currentPage++;
          }
        }
      }

      console.log(`\nPagination stopped. Found ${historyItems.length} total items across ${currentPage} pages`);

      // Filter by year if specified
      let filteredItems = historyItems;
      if (year) {
        filteredItems = historyItems.filter(item => {
          if (!item.lastVisited) return false;
          return item.lastVisited.getFullYear() === parseInt(year);
        });
        console.log(`Filtered to ${filteredItems.length} items for year ${year}`);
      }

      return filteredItems;

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

      // Wait before retrying (exponential backoff with longer delays)
      const waitTime = attempt * 10000;
      console.log(`Retrying in ${waitTime/1000} seconds...`);
      await delay(waitTime);
    }
  }

  throw new Error('All retry attempts failed');
}

export { scrapeAO3History };
