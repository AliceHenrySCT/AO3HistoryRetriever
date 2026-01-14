# AO3 History Scraper

A web application that retrieves your reading history from Archive of Our Own (AO3). This tool allows you to backup and view all the works you've read on AO3.

## Why Deploy This?

This application requires a real server environment to work. Browser-based development environments like StackBlitz or CodeSandbox cannot make outbound HTTPS requests to external websites like AO3 due to security restrictions. You must deploy this to a hosting service or run it locally.

## Deploy to Render (Recommended)

Render is a free hosting platform that's perfect for this application.

### Quick Deploy

1. Create a free account at [Render.com](https://render.com)

2. Click "New +" and select "Web Service"

3. Connect your GitHub repository (or upload this code to GitHub first)

4. Render will automatically detect the `render.yaml` configuration

5. Click "Create Web Service"

6. Wait for deployment to complete (2-3 minutes)

7. Access your app at the provided Render URL (e.g., `https://your-app-name.onrender.com`)

### Manual Configuration

If automatic detection doesn't work:

- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `python app.py`
- **Environment**: Python 3.11

## Run Locally

If you prefer to run this on your own computer:

1. Install Python (3.11 or higher)

2. Clone or download this project

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Start the server:
   ```bash
   python app.py
   ```

5. Open your browser to `http://localhost:3000`

## How to Use

1. Open the application in your browser

2. Enter your AO3 username and password

3. Optionally select a year to filter results

4. Click "Scrape History"

5. Your reading history will be displayed with statistics

## Security Notes

- Your credentials are only used to log into AO3 and are not stored anywhere
- All requests are made from the server, not your browser
- The application uses secure HTTPS connections
- No data is saved or logged after the request completes

## Troubleshooting

### "Connection failed" error

- Check that the server is running
- Verify your internet connection
- AO3 may be temporarily down or slow

### "Invalid username or password" error

- Double-check your credentials
- Try logging into AO3 directly in your browser first

### "Rate limited" error

- AO3 has detected too many requests
- Wait 5-10 minutes before trying again
- This is an AO3 protection mechanism

### Timeout errors

- AO3 may be experiencing high traffic
- Try again in a few minutes
- The scraper automatically retries up to 3 times

## Technical Details

- Built with Python and Flask
- Uses BeautifulSoup for HTML parsing
- Implements session-based cookie management
- Includes retry logic and rate limiting protection
- Respects AO3's robots.txt and rate limits
- Scrapes all pages of reading history with year filtering

## Limitations

- Requires AO3 credentials (no guest access)
- Subject to AO3's rate limiting and availability
- Cannot work in browser-only environments
- Includes automatic delays to avoid rate limiting

## License

This is a personal tool for backing up your own data. Use responsibly and respect AO3's terms of service.
