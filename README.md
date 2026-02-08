# SteamDB-Technologies-Scraper-Tool
Scrape through different technologies from SteamDB

A robust Python tool that scrapes SteamDB.info to extract comprehensive data about game technologies, engines, SDKs, containers, emulators, launchers, and anti-cheat systems using Selenium with AJAX optimization.

## Features

- **Dual-Method Scraping**: First attempts AJAX requests for faster data retrieval, falls back to Selenium when needed
- **Cloudflare Bypass**: Handles Cloudflare anti-bot challenges automatically (Partially)
- **Comprehensive Data Collection**: Extracts data from multiple technology categories (Engine, SDK, Container, Emulator, Launcher, AntiCheat)
- **Pagination Support**: Automatically navigates through multiple pages of game listings
- **Rich Game Data**: Captures app IDs, names, Steam/SteamDB links, images, release dates, reviews, and tags
- **Configurable Filtering**: Filter by minimum review counts and technology popularity
- **Detailed Logging**: Comprehensive logging with file and console output
- **Debug Tools**: Saves screenshots, HTML snapshots, and table data for troubleshooting

## Installation

### Prerequisites

- Python 3.7+
- Google Chrome browser
- ChromeDriver (automatically managed by the tool)

### Install Dependencies

```bash
pip install selenium webdriver-manager beautifulsoup4 requests
```

## Usage

### Basic Usage

```bash
# Run with default settings
python steamdb_selenium_parser.py

# Run in headless mode (no browser window)
python steamdb_selenium_parser.py --headless

# Test mode - only fetch categories without games
python steamdb_selenium_parser.py --test
```

### Advanced Options

```bash
# Customize scraping parameters
python steamdb_selenium_parser.py \
    --headless \
    --min-count 500 \
    --min-reviews 100 \
    --max-pages 50 \
    --output my_data.json \
    --categories "Engine,SDK" \
    --limit-tech 10
```

### Command Line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--headless` | Run browser in headless mode | False |
| `--min-count` | Minimum game count for technology inclusion | 1000 |
| `--min-reviews` | Minimum reviews for individual games | 500 |
| `--max-pages` | Maximum pages to scrape per technology | 100 |
| `--output` | Output JSON file name | `steamdb_selenium.json` |
| `--test` | Test mode - fetch only categories | False |
| `--categories` | Categories to scrape (comma-separated) | `Engine` |
| `--limit-tech` | Limit technologies per category | 5 |

## Output Format

The tool generates a JSON file with the following structure:

```json
{
  "metadata": {
    "generated_at": "2024-01-01T12:00:00",
    "source": "SteamDB",
    "base_url": "https://steamdb.info",
    "method": "selenium_with_ajax_fallback",
    "total_categories": 3,
    "total_technologies": 15,
    "total_games": 2500
  },
  "technologies": {
    "Engine": {
      "Unity": {
        "data_s": "Unity",
        "link": "/tech/Engine/Unity/",
        "count": 1500,
        "games": [
          {
            "appid": "730",
            "name": "Counter-Strike 2",
            "steam_link": "https://store.steampowered.com/app/730/",
            "steamdb_link": "https://steamdb.info/app/730/",
            "image_link": "https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/730/capsule_231x87.jpg",
            "release_date": "2012-08-21",
            "reviews": "1,234,567",
            "positive_percentage": "96%",
            "tags": ["Action", "FPS", "Multiplayer"]
          }
        ]
      }
    }
  }
}
```

## How It Works

### 1. Technology Discovery
- Navigates to SteamDB's technology pages
- Extracts all available technology categories
- Captures technology metadata (name, link, game count)

### 2. Game Collection (AJAX First)
1. **AJAX Method**: Attempts to fetch data via SteamDB's internal API
   - Extracts AJAX endpoints from page source
   - Uses session cookies from Selenium
   - Parses JSON responses efficiently

2. **Selenium Fallback**: If AJAX fails, uses Selenium
   - Simulates human browsing patterns
   - Handles JavaScript-rendered content
   - Manages pagination through DataTables

### 3. Data Processing
- Cleans and validates extracted data
- Removes duplicates
- Applies user-defined filters (min reviews, etc.)
- Structures data for easy consumption

## Technology Categories

The tool scrapes these main categories:

| Category | Description | Examples |
|----------|-------------|----------|
| **Engine** | Game engines and frameworks | Unity, Unreal Engine, Godot |
| **SDK** | Software development kits | Steamworks, NVIDIA PhysX |
| **Container** | Runtime containers | Proton, Wine |
| **Emulator** | Compatibility layers | DOSBox, ScummVM |
| **Launcher** | Game launchers | Epic Games Launcher, Uplay |
| **AntiCheat** | Anti-cheat systems | Easy Anti-Cheat, BattlEye |

## Practical Applications

### For Game Developers
- **Technology Analysis**: Research popular game engines and SDKs
- **Market Research**: Understand technology adoption trends
- **Competitor Analysis**: See what technologies successful games use

### For Modders & Enthusiasts
- **Modding Discovery**: Find games using mod-friendly engines
- **Compatibility Research**: Identify games using specific containers/emulators
- **Learning Resources**: Study games that use particular technologies

### For Data Analysts
- **Trend Analysis**: Track technology adoption over time
- **Correlation Studies**: Link technologies to game success metrics
- **Dataset Creation**: Build comprehensive game technology databases

## Troubleshooting

### Common Issues

1. **ChromeDriver Errors**
   ```
   Solution: The tool uses webdriver-manager to auto-manage ChromeDriver.
   Make sure Chrome is installed and updated.
   ```

2. **Cloudflare Challenges**
   ```
   The tool automatically handles Cloudflare challenges with increased wait times.
   Check steamdb_selenium.log for details.
   ```

3. **No Data Extracted**
   ```
   Check saved files:
   - tech_categories.png (screenshot of the page)
   - current_page.html (HTML source)
   - steamdb_selenium.log (detailed logs)
   ```

### Debug Files Generated

| File | Purpose |
|------|---------|
| `steamdb_selenium.log` | Detailed process logs |
| `tech_categories.png` | Screenshot of technology page |
| `current_page.html` | HTML of last visited page |
| `cloudflare_complete.png` | Screenshot after Cloudflare challenge |
| `table_*.html` | Extracted table HTML for debugging |
| `debug_*.html` | Full page HTML for problematic pages |

## Performance Tips

1. **Use Headless Mode**: `--headless` for faster execution
2. **Adjust Limits**: Reduce `--max-pages` and `--limit-tech` for quicker runs
3. **Increase Minimums**: Use `--min-count` and `--min-reviews` to filter less popular items
4. **Select Categories**: Use `--categories` to only scrape needed categories

## Ethical Considerations

⚠️ **Use Responsibly**
- This tool is for educational and research purposes only
- Respect SteamDB's terms of service and robots.txt
- Add delays between requests to avoid overloading servers
- Consider using official APIs when available
- Do not use for commercial purposes without permission

## Comparison with Similar Tools

| Feature | This Tool | Other Scrapers |
|---------|-----------|----------------|
| AJAX Optimization | ✅ First attempts AJAX | ❌ Usually pure Selenium |
| Cloudflare Handling | ✅ Built-in with wait logic | ❌ Often fails |
| Dual Parsing Methods | ✅ Regex + Selenium extraction | ❌ Single method |
| Category Filtering | ✅ Multiple categories | ❌ Usually single category |
| Debug Tools | ✅ Screenshots, HTML dumps | ❌ Limited debugging |
| Pagination Support | ✅ Full DataTables support | ⚠️ Often limited |

## Related Projects

- [Steam and PSN Game Scraper / Game Engine - SDK Comparisor](https://github.com/kalevi00011/Steam-and-PSN-Game-Scraper-Game-Engine---SDK-Comparisor) - Companion tool for game engine analysis and comparison

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is for educational purposes. Please respect SteamDB's terms of service and use responsibly.

## Acknowledgments

- SteamDB for providing comprehensive game data
- Selenium and BeautifulSoup communities
- Open-source contributors to web scraping tools

---

Built with ❤️ for game data enthusiasts AND for the new becomers who want to start game modding and does not know about Engines and Tech ;)

⚠️ Use responsibly and ethically

THIS README WAS WRITTEN WITH AI(DEEPSEEK) FOR TAKING CARE OF THE PROPER SYNTAX AND GRAMMAR! THANKS AND SORRY <3
