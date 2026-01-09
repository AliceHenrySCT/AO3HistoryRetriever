const express = require('express');
const { scrapeAO3History } = require('./ao3_scraper');

const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.json());
app.use(express.static('public'));

// Health check endpoint
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// Test AO3 connectivity
app.get('/api/test-connection', async (req, res) => {
  const axios = require('axios');
  const https = require('https');

  console.log('Testing connection to AO3...');

  try {
    const httpsAgent = new https.Agent({
      keepAlive: true,
      timeout: 30000,
      rejectUnauthorized: true
    });

    const response = await axios.get('https://archiveofourown.org/', {
      timeout: 30000,
      httpsAgent: httpsAgent,
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
      }
    });

    console.log('Connection test successful. Status:', response.status);

    res.json({
      success: true,
      status: response.status,
      message: 'Successfully connected to AO3'
    });
  } catch (error) {
    console.error('Connection test failed:', error.message);
    console.error('Error code:', error.code);

    res.status(500).json({
      success: false,
      error: error.message,
      code: error.code,
      message: 'Failed to connect to AO3'
    });
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
