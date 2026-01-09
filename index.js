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

app.post('/api/scrape', async (req, res) => {
  const { username, password } = req.body;

  if (!username || !password) {
    return res.status(400).json({ error: 'Username and password required' });
  }

  console.log(`Starting scrape for user: ${username}`);

  try {
    const historyItems = await scrapeAO3History(username, password);
    console.log(`Successfully scraped ${historyItems.length} items`);
    res.json(historyItems);
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
