import express from 'express';
import { scrapeAO3History } from './ao3_scraper.js';
import axios from 'axios';

console.log('Node version:', process.version);
console.log('Express and scraper loaded successfully');

const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.json());
app.use(express.static('public'));

// Health check endpoint
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// Rate limiting for test connections
let lastTestTime = 0;
const TEST_COOLDOWN = 10000; // 10 seconds between tests

// Test AO3 connectivity
app.get('/api/test-connection', async (req, res) => {
  console.log('Testing connection to AO3...');

  // Check rate limiting
  const now = Date.now();
  const timeSinceLastTest = now - lastTestTime;
  if (timeSinceLastTest < TEST_COOLDOWN) {
    const waitTime = Math.ceil((TEST_COOLDOWN - timeSinceLastTest) / 1000);
    return res.status(429).json({
      success: false,
      message: `Please wait ${waitTime} seconds before testing again`,
      waitTime
    });
  }

  try {
    // Add delay before making request to avoid rate limiting
    await new Promise(resolve => setTimeout(resolve, 2000));

    const response = await axios.get('https://archiveofourown.org/', {
      timeout: 60000,
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
    });

    lastTestTime = Date.now();
    console.log('Connection test successful. Status:', response.status);
    console.log('Response headers:', JSON.stringify(response.headers, null, 2));

    if (response.status === 429) {
      const retryAfter = response.headers['retry-after'];
      console.error('Rate limit detected (429) during test!');
      console.error('Retry-After header:', retryAfter);

      return res.status(429).json({
        success: false,
        status: response.status,
        error: 'Rate Limited',
        retryAfter: retryAfter,
        message: `AO3 returned 429 (Rate Limited). ${retryAfter ? `Retry after ${retryAfter} seconds.` : 'Please wait and try again later.'}`
      });
    }

    if (response.status === 403) {
      console.error('403 Forbidden detected during test - possible bot detection');

      return res.status(403).json({
        success: false,
        status: response.status,
        error: 'Forbidden',
        message: 'AO3 returned 403 Forbidden. This may indicate bot detection or IP blocking.'
      });
    }

    if (response.status === 503) {
      console.error('503 Service Unavailable during test');

      return res.status(503).json({
        success: false,
        status: response.status,
        error: 'Service Unavailable',
        message: 'AO3 is temporarily unavailable (503). Please try again later.'
      });
    }

    if (response.status >= 400) {
      console.error(`Unexpected status code during test: ${response.status}`);

      return res.status(response.status).json({
        success: false,
        status: response.status,
        error: `HTTP ${response.status}`,
        message: `AO3 returned error status ${response.status}`
      });
    }

    res.json({
      success: true,
      status: response.status,
      message: 'Successfully connected to AO3',
      headers: response.headers
    });
  } catch (error) {
    lastTestTime = Date.now();
    console.error('Connection test failed:', error.message);
    console.error('Error code:', error.code);

    if (error.response) {
      console.error('Response status:', error.response.status);
      console.error('Response headers:', JSON.stringify(error.response.headers, null, 2));
    }

    let errorMessage = 'Failed to connect to AO3.';
    let errorDetails = {
      success: false,
      error: error.message,
      code: error.code
    };

    if (error.code === 'ECONNABORTED' || error.code === 'ETIMEDOUT') {
      errorMessage = 'Connection timed out. AO3 may be slow or unavailable.';
    } else if (error.code === 'ECONNREFUSED') {
      errorMessage = 'Connection refused. AO3 may be down or blocking requests.';
    } else if (error.code === 'ENOTFOUND') {
      errorMessage = 'Could not reach AO3. Please check your internet connection.';
    } else if (error.code === 'ECONNRESET') {
      errorMessage = 'Connection was reset. This may indicate rate limiting or network issues.';
    } else if (error.response) {
      errorDetails.status = error.response.status;
      errorMessage = `AO3 returned status ${error.response.status}`;
    }

    errorDetails.message = errorMessage;

    res.status(500).json(errorDetails);
  }
});

function calculateStatistics(historyItems) {
  const stats = {
    totalFics: historyItems.length,
    totalWords: 0,
    topTags: [],
    topShips: [],
    topFandoms: []
  };

  const tagCounts = {};
  const shipCounts = {};
  const fandomCounts = {};

  historyItems.forEach(item => {
    stats.totalWords += item.wordCount || 0;

    item.tags?.forEach(tag => {
      tagCounts[tag] = (tagCounts[tag] || 0) + 1;
    });

    item.relationships?.forEach(ship => {
      shipCounts[ship] = (shipCounts[ship] || 0) + 1;
    });

    item.fandoms?.forEach(fandom => {
      fandomCounts[fandom] = (fandomCounts[fandom] || 0) + 1;
    });
  });

  stats.topTags = Object.entries(tagCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
    .map(([tag, count]) => ({ tag, count }));

  stats.topShips = Object.entries(shipCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
    .map(([ship, count]) => ({ ship, count }));

  stats.topFandoms = Object.entries(fandomCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
    .map(([fandom, count]) => ({ fandom, count }));

  return stats;
}

app.get('/api/scrape-stream', async (req, res) => {
  const { username, password, year } = req.query;

  if (!username || !password) {
    res.writeHead(400, { 'Content-Type': 'text/event-stream' });
    res.write(`event: error\ndata: ${JSON.stringify({ error: 'Username and password required' })}\n\n`);
    res.end();
    return;
  }

  console.log(`Starting scrape for user: ${username}${year ? ` (Year: ${year})` : ''}`);

  res.writeHead(200, {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive'
  });

  const onProgress = (progressData) => {
    res.write(`event: progress\ndata: ${JSON.stringify(progressData)}\n\n`);
  };

  try {
    const historyItems = await scrapeAO3History(username, password, year, 3, onProgress);
    console.log(`Successfully scraped ${historyItems.length} items`);

    const statistics = calculateStatistics(historyItems);

    res.write(`event: complete\ndata: ${JSON.stringify({ items: historyItems, statistics })}\n\n`);
    res.end();
  } catch (error) {
    console.error('Scraping error:', error.message);
    res.write(`event: error\ndata: ${JSON.stringify({ error: error.message || 'Failed to scrape history' })}\n\n`);
    res.end();
  }
});

app.post('/api/scrape', async (req, res) => {
  const { username, password, year } = req.body;

  if (!username || !password) {
    return res.status(400).json({ error: 'Username and password required' });
  }

  console.log(`Starting scrape for user: ${username}${year ? ` (Year: ${year})` : ''}`);

  try {
    const historyItems = await scrapeAO3History(username, password, year);
    console.log(`Successfully scraped ${historyItems.length} items`);

    const statistics = calculateStatistics(historyItems);

    res.json({
      items: historyItems,
      statistics
    });
  } catch (error) {
    console.error('Scraping error:', error.message);
    res.status(500).json({
      error: error.message || 'Failed to scrape history. Please check your credentials.'
    });
  }
});

app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
  console.log(`Health check available at: http://localhost:${PORT}/api/health`);
});
