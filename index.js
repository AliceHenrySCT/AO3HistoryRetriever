import express from 'express';
import { scrapeAO3History } from './ao3_scraper.js';

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

// Debug endpoint to test reading history page structure
app.get('/api/debug-history', async (req, res) => {
  const { username, password } = req.query;

  if (!username || !password) {
    return res.status(400).json({ error: 'Username and password required' });
  }

  try {
    const result = await scrapeAO3History(username, password, null, 1, null);
    res.json({
      success: true,
      itemCount: result.length,
      message: 'Check server logs for detailed debug output'
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

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
