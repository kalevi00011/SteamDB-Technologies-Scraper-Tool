import json
import time
import logging
from typing import Dict, List, Optional
from datetime import datetime
import sys
import re
import random
import requests
from urllib.parse import urljoin

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('steamdb_selenium.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Global imports for Selenium
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
    from webdriver_manager.chrome import ChromeDriverManager
    from bs4 import BeautifulSoup
    HAS_SELENIUM = True
except ImportError as e:
    logger.error(f"Required imports failed: {e}")
    HAS_SELENIUM = False

class SteamDBSeleniumParser:
    def __init__(self, headless: bool = False):
        if not HAS_SELENIUM:
            raise ImportError("Required packages not installed. Please install: pip install selenium webdriver-manager beautifulsoup4 requests")
        
        self.headless = headless
        self.driver = None
        self.base_url = 'https://steamdb.info'
        
        # For AJAX requests
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'en-US,en;q=0.9',
        })
        
        logger.info(f"Initialized SteamDBSeleniumParser (headless={headless})")
    
    def setup_driver(self):
        """Setup Chrome driver with appropriate options"""
        chrome_options = Options()
        
        # Add arguments to make Chrome look more like a real browser
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Add user agent
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36')
        
        # Window size
        chrome_options.add_argument('--window-size=1920,1080')
        
        if self.headless:
            chrome_options.add_argument('--headless')
        
        # Disable dev shm usage
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-extensions')
        
        # Add language preference
        chrome_options.add_argument('--lang=en-US,en;q=0.9')
        
        try:
            # Use webdriver-manager to automatically manage ChromeDriver
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Execute CDP commands to avoid detection
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            logger.info("ChromeDriver setup complete")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup ChromeDriver: {e}")
            print("\n" + "="*60)
            print("CHROMEDRIVER SETUP FAILED")
            print("="*60)
            print(f"Error: {e}")
            print("="*60)
            return False
    
    def wait_for_element(self, by, value, timeout=30):
        """Wait for element to be present"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return element
        except TimeoutException:
            logger.warning(f"Timeout waiting for element: {value}")
            return None
    
    def navigate_to_url(self, url: str):
        """Navigate to URL and handle Cloudflare challenges"""
        full_url = url if url.startswith('http') else f"{self.base_url}{url}"
        logger.info(f"Navigating to: {full_url}")
        
        try:
            self.driver.get(full_url)
            
            # Wait for page to load
            time.sleep(5)
            
            # Check for Cloudflare challenge
            page_source = self.driver.page_source
            
            if 'Checking your browser' in page_source or 'cf-browser-verification' in page_source:
                logger.warning("Cloudflare challenge detected")
                print("\n⚠️ Cloudflare challenge detected. Waiting for it to complete...")
                
                # Wait for challenge to complete
                for i in range(1, 61):  # Increased to 60 seconds
                    time.sleep(1)
                    current_source = self.driver.page_source
                    if 'Checking your browser' not in current_source:
                        logger.info(f"Cloudflare challenge completed after {i} seconds")
                        break
                    
                    if i % 5 == 0:
                        print(f"  Still waiting... ({i}/60 seconds)")
                
                # Take screenshot
                try:
                    self.driver.save_screenshot('cloudflare_complete.png')
                    logger.info("Saved screenshot after Cloudflare challenge")
                except:
                    pass
            
            # Wait a bit more for content to load
            time.sleep(3)
            
            # Save page source for debugging
            try:
                with open('current_page.html', 'w', encoding='utf-8') as f:
                    f.write(self.driver.page_source[:50000])  # First 50k chars
                logger.info("Saved page source to current_page.html")
            except:
                pass
            
            logger.info("Navigation successful")
            return True
            
        except Exception as e:
            logger.error(f"Failed to navigate to {full_url}: {e}")
            return False
    
    def get_all_technologies(self) -> Dict:
        """Get all technology categories using Selenium"""
        if not self.navigate_to_url('/tech/'):
            logger.error("Failed to navigate to tech page")
            return {}
        
        # Take screenshot
        try:
            self.driver.save_screenshot('tech_categories.png')
            logger.info("Saved screenshot to tech_categories.png")
        except:
            pass
        
        # Get page source and parse with BS for categories (since it's static)
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        
        categories = {}
        target_categories = ['Engine', 'SDK', 'Container', 'Emulator', 'Launcher', 'AntiCheat']
        
        logger.info(f"Looking for categories: {target_categories}")
        
        for category_id in target_categories:
            logger.info(f"Processing category: {category_id}")
            
            h2 = soup.find('h2', id=category_id)
            if not h2:
                logger.warning(f"Category '{category_id}' not found")
                continue
            
            logger.info(f"Found category header for '{category_id}'")
            category_name = category_id
            categories[category_name] = {}
            
            taglist = h2.find_next('div', class_='taglist')
            if not taglist:
                next_sibling = h2.find_next_sibling('div')
                if next_sibling and 'taglist' in next_sibling.get('class', []):
                    taglist = next_sibling
            
            if not taglist:
                logger.warning(f"No taglist found for '{category_id}'")
                continue
            
            labels = taglist.find_all('div', class_='label')
            logger.info(f"Found {len(labels)} technologies in '{category_id}'")
            
            for label in labels:
                try:
                    a_tag = label.find('a', class_='label-link')
                    if not a_tag:
                        continue
                    
                    tech_name = a_tag.text.strip()
                    tech_link = a_tag.get('href', '')
                    
                    count_span = label.find('span', class_='label-count')
                    count = 0
                    if count_span:
                        count_text = count_span.text.strip().replace(',', '')
                        if count_text.isdigit():
                            count = int(count_text)
                    
                    data_s = label.get('data-s', tech_name)
                    
                    categories[category_name][tech_name] = {
                        'data_s': data_s,
                        'link': tech_link,
                        'count': count,
                        'games': []
                    }
                    
                    logger.debug(f"  Added technology: {tech_name} ({count} games)")
                    
                except Exception as e:
                    logger.error(f"Error parsing label: {e}")
                    continue
        
        logger.info(f"Found {len(categories)} categories with total technologies: {sum(len(t) for t in categories.values())}")
        
        if categories:
            print("\n" + "="*60)
            print("CATEGORIES FOUND")
            print("="*60)
            for cat_name, techs in categories.items():
                print(f"{cat_name}: {len(techs)} technologies")
                sorted_techs = sorted(techs.items(), key=lambda x: x[1]['count'], reverse=True)[:5]
                for tech_name, tech_info in sorted_techs:
                    print(f"  - {tech_name}: {tech_info['count']} games")
            print("="*60)
        
        return categories
    
    def get_games_for_technology(self, tech_link: str, tech_name: str, 
                                min_reviews: int = 500, max_pages: int = 100) -> List[Dict]:
        """Get games for a specific technology - tries AJAX first, falls back to Selenium"""
        logger.info(f"Fetching games for: {tech_name}")
        
        # Try AJAX method first
        ajax_games = self._try_ajax_method(tech_link, tech_name, min_reviews)
        if ajax_games:
            logger.info(f"AJAX method successful for {tech_name}, found {len(ajax_games)} games")
            return ajax_games
        
        # If AJAX fails, fall back to original Selenium method
        logger.info(f"Falling back to Selenium method for {tech_name}")
        return self._get_games_selenium_fallback(tech_link, tech_name, min_reviews, max_pages)
    
    def _try_ajax_method(self, tech_link: str, tech_name: str, min_reviews: int) -> List[Dict]:
        """Try to get games via AJAX request"""
        try:
            # First navigate to the page to get cookies
            if not tech_link.startswith('/'):
                tech_link = '/' + tech_link
            
            if '?min_reviews=' in tech_link:
                tech_link = tech_link.split('?min_reviews=')[0]
            
            url = f"{tech_link}?min_reviews={min_reviews}"
            
            if not self.navigate_to_url(url):
                return []
            
            # Get cookies from Selenium
            cookies = self.driver.get_cookies()
            
            # Create session with cookies
            session = requests.Session()
            for cookie in cookies:
                session.cookies.set(cookie['name'], cookie['value'])
            
            # Add headers
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'Referer': self.driver.current_url,
            })
            
            # Try to find AJAX endpoint in page source
            page_source = self.driver.page_source
            ajax_url = None
            
            # Look for DataTables AJAX configuration
            ajax_patterns = [
                r'"ajax"\s*:\s*"([^"]+)"',
                r'ajax:\s*["\']([^"\']+)["\']',
                r'url:\s*["\']([^"\']+data[^"\']*)["\']'
            ]
            
            for pattern in ajax_patterns:
                match = re.search(pattern, page_source, re.IGNORECASE)
                if match:
                    ajax_url = match.group(1)
                    if ajax_url.startswith('/'):
                        ajax_url = f"{self.base_url}{ajax_url}"
                    break
            
            # If not found, try common pattern
            if not ajax_url and '/tech/' in tech_link:
                # Common pattern: /tech/Engine/Unity/data/
                parts = tech_link.strip('/').split('/')
                if len(parts) >= 3:
                    category = parts[1]
                    tech_slug = parts[2]
                    ajax_url = f"{self.base_url}/tech/{category}/{tech_slug}/data/"
            
            if not ajax_url:
                logger.warning(f"No AJAX URL found for {tech_name}")
                return []
            
            logger.info(f"Found AJAX endpoint: {ajax_url}")
            
            # Make AJAX request
            params = {
                'draw': '1',
                'start': '0',
                'length': '100',
                'min_reviews': str(min_reviews),
                'search[value]': '',
                'search[regex]': 'false',
                'order[0][column]': '0',
                'order[0][dir]': 'asc'
            }
            
            response = session.get(ajax_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            games = []
            rows_data = data.get('data', [])
            
            for row_data in rows_data:
                if isinstance(row_data, list) and len(row_data) >= 2:
                    game = self._parse_ajax_game_row(row_data)
                    if game:
                        games.append(game)
            
            logger.info(f"AJAX method retrieved {len(games)} games for {tech_name}")
            return games
            
        except Exception as e:
            logger.warning(f"AJAX method failed for {tech_name}: {e}")
            return []
    
    def _parse_ajax_game_row(self, row_data: list) -> Optional[Dict]:
        """Parse game data from AJAX response row"""
        try:
            # Second column (index 1) usually contains game name and link
            if len(row_data) < 2:
                return None
            
            cell_html = row_data[1]
            soup = BeautifulSoup(cell_html, 'html.parser')
            
            # Find app link
            app_link = soup.find('a', href=re.compile(r'/app/\d+/'))
            if not app_link:
                return None
            
            href = app_link.get('href', '')
            appid_match = re.search(r'/app/(\d+)', href)
            if not appid_match:
                return None
            
            appid = appid_match.group(1)
            name = app_link.get_text(strip=True)
            
            if not name or not appid:
                return None
            
            # Get additional info from other columns if available
            additional_info = {}
            
            # Release date (usually column 2)
            if len(row_data) > 2:
                release_soup = BeautifulSoup(row_data[2], 'html.parser')
                release_date = release_soup.get_text(strip=True)
                if release_date:
                    additional_info['release_date'] = release_date
            
            # Reviews (usually column 3)
            if len(row_data) > 3:
                reviews_soup = BeautifulSoup(row_data[3], 'html.parser')
                reviews = reviews_soup.get_text(strip=True)
                if reviews:
                    additional_info['reviews'] = reviews
            
            game_data = {
                'appid': appid,
                'name': name,
                'steam_link': f"https://store.steampowered.com/app/{appid}/",
                'steamdb_link': f"{self.base_url}/app/{appid}/",
                'image_link': f"https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/{appid}/capsule_231x87.jpg",
                **additional_info
            }
            
            return game_data
            
        except Exception as e:
            logger.debug(f"Error parsing AJAX row: {e}")
            return None
    
    def _get_games_selenium_fallback(self, tech_link: str, tech_name: str, 
                                    min_reviews: int, max_pages: int) -> List[Dict]:
        """Original Selenium fallback method with fixed DataTables pagination"""
        if not tech_link.startswith('/'):
            tech_link = '/' + tech_link
        
        if '?min_reviews=' in tech_link:
            tech_link = tech_link.split('?min_reviews=')[0]
        
        url = f"{tech_link}?min_reviews={min_reviews}"
        
        logger.info(f"Navigating to: {url}")
        
        if not self.navigate_to_url(url):
            logger.warning(f"Failed to navigate to {tech_name} page")
            return []
        
        # Wait for dynamic table to load
        try:
            WebDriverWait(self.driver, 30).until_not(
                EC.visibility_of_element_located((By.CSS_SELECTOR, ".dataTables_processing"))
            )
            logger.info("Processing indicator disappeared")
        except TimeoutException:
            logger.warning("No processing indicator found or timeout")
        
        # Wait for table to load
        try:
            WebDriverWait(self.driver, 120).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table.dataTable tbody tr"))
            )
            logger.info("DataTable loaded with rows")
            time.sleep(2)
        except TimeoutException:
            logger.warning("Timeout waiting for DataTable rows")
            safe_name = re.sub(r'[^\w\-_]', '_', tech_name)[:50]
            with open(f'debug_{safe_name}_load_fail.html', 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            logger.info(f"Saved debug HTML to debug_{safe_name}_load_fail.html")
            return []
        
        # Save the table HTML for debugging
        try:
            table_element = self.driver.find_element(By.CSS_SELECTOR, "table.dataTable")
            table_html = table_element.get_attribute('outerHTML')
            safe_name = re.sub(r'[^\w\-_]', '_', tech_name)[:50]
            with open(f'table_{safe_name}.html', 'w', encoding='utf-8') as f:
                f.write(table_html)
            logger.info(f"Saved table HTML to table_{safe_name}.html")
        except Exception as e:
            logger.warning(f"Could not save table HTML: {e}")
        
        games = []
        page = 1
        last_game_count = 0
        
        while page <= max_pages:
            logger.info(f"  Processing page {page} of {tech_name}")
            
            # Parse games from current page
            page_games = self._parse_games_from_current_page()
            
            # Check if we got new games or same as last page
            current_game_count = len(games)
            if page_games:
                # Add only new games (avoid duplicates)
                for game in page_games:
                    if not any(g['appid'] == game['appid'] for g in games):
                        games.append(game)
            
            new_games_count = len(games) - current_game_count
            logger.info(f"    Found {new_games_count} new games on page {page} (Total: {len(games)})")
            
            if len(page_games) == 0:
                logger.warning("No games found on current page. Checking page content...")
                safe_name = re.sub(r'[^\w\-_]', '_', tech_name)[:50]
                with open(f'debug_{safe_name}_page{page}.html', 'w', encoding='utf-8') as f:
                    f.write(self.driver.page_source[:20000])
                logger.info(f"Saved debug HTML to debug_{safe_name}_page{page}.html")
            
            # Try to go to next page using DataTables pagination buttons
            if not self._click_next_page_data_tables():
                logger.info("No more pages available")
                break
            
            page += 1
            time.sleep(2)  # Wait between pages
    
        logger.info(f"  Total unique games found for {tech_name}: {len(games)}")
        return games
    
    def _click_next_page_data_tables(self) -> bool:
        """Click the next page button in DataTables and return True if successful"""
        try:
            # Find pagination container
            pagination = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.dataTables_paginate"))
            )
            
            # Get current active page
            active_page = pagination.find_element(By.CSS_SELECTOR, "button.dt-paging-button.active")
            current_page = active_page.text.strip()
            logger.info(f"Current page: {current_page}")
            
            # Get all pagination buttons
            buttons = pagination.find_elements(By.CSS_SELECTOR, "button.dt-paging-button")
            
            next_button = None
            
            # First try to find next numbered page
            for button in buttons:
                button_text = button.text.strip()
                if button_text.isdigit() and button_text == str(int(current_page) + 1):
                    next_button = button
                    logger.info(f"Found next page button: {button_text}")
                    break
            
            # If not found, look for "next" arrow (› or >)
            if not next_button:
                for button in buttons:
                    button_text = button.text.strip()
                    if button_text in ['›', '>', '»', 'Next']:
                        next_button = button
                        logger.info(f"Found next arrow button: {button_text}")
                        break
            
            if next_button:
                # Check if next button is disabled
                classes = next_button.get_attribute('class')
                if 'disabled' in classes:
                    logger.info("Next button is disabled")
                    return False
                
                # Scroll to the button
                self.driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                time.sleep(0.5)
                
                # Click using JavaScript
                self.driver.execute_script("arguments[0].click();", next_button)
                logger.info(f"Clicked next page button")
                
                # Wait for new page to load
                time.sleep(3)
                
                # Wait for processing to complete
                try:
                    WebDriverWait(self.driver, 30).until_not(
                        EC.visibility_of_element_located((By.CSS_SELECTOR, ".dataTables_processing"))
                    )
                    logger.info("Next page loaded successfully")
                    
                    # Wait for table to update
                    WebDriverWait(self.driver, 30).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "table.dataTable tbody tr"))
                    )
                    
                    return True
                    
                except TimeoutException:
                    logger.warning("Timeout waiting for next page to load")
                    return False
                    
            else:
                logger.info("No next page button found")
                return False
                
        except TimeoutException:
            logger.warning("Timeout finding pagination")
            return False
        except NoSuchElementException:
            logger.info("No pagination found, assuming single page")
            return False
        except Exception as e:
            logger.error(f"Error clicking next page: {e}")
            return False
    
    def _parse_games_from_current_page(self) -> List[Dict]:
        """Parse games from current page using Selenium elements"""
        games = []
        
        # First try the simple regex method
        simple_games = self._parse_games_from_current_page_simple()
        if simple_games:
            return simple_games
        
        # If simple method failed, try the detailed parsing
        # Find rows
        try:
            rows = self.driver.find_elements(By.CSS_SELECTOR, 'table.dataTable tbody tr')
            logger.info(f"Found {len(rows)} rows using Selenium")
        except Exception as e:
            logger.error(f"Error finding rows: {e}")
            return games
        
        for row in rows:
            try:
                game_data = self._extract_game_data_from_row(row)
                if game_data:
                    games.append(game_data)
                    logger.debug(f"  Found game: {game_data['name']} (AppID: {game_data['appid']})")
            
            except Exception as e:
                logger.error(f"Error parsing game row: {e}")
                continue
    
        return games
    
    def _parse_games_from_current_page_simple(self) -> List[Dict]:
        """Simple parsing method for DataTables - just get appids and names from HTML"""
        games = []
        
        try:
            # Get the entire table HTML
            table_html = self.driver.page_source
            
            # Use regex to find all app links - updated for DataTables structure
            app_patterns = [
                # Pattern for DataTables links: /app/123456/
                r'href=["\']/app/(\d+)/["\'][^>]*>([^<]+)</a>',
                r'/app/(\d+)/["\'][^>]*>([^<]+)</a>',
                # Pattern with title attribute
                r'/app/(\d+)/["\'][^>]*title=["\']([^"\']+)["\']',
                # Pattern with data-order attribute (common in DataTables)
                r'data-order=["\'][^"\']*?["\'][^>]*/app/(\d+)/["\'][^>]*>([^<]+)<',
            ]
            
            for pattern in app_patterns:
                matches = re.findall(pattern, table_html, re.IGNORECASE)
                for match in matches:
                    appid = match[0]
                    name = match[1].strip()
                    
                    if appid and name and len(name) > 1:
                        # Clean up name
                        name = re.sub(r'\s+', ' ', name)  # Remove extra whitespace
                        name = re.sub(r'\s*<span[^>]*>.*?</span>', '', name)  # Remove span tags
                        
                        game_data = {
                            'appid': appid,
                            'name': name,
                            'steam_link': f"https://store.steampowered.com/app/{appid}/",
                            'steamdb_link': f"{self.base_url}/app/{appid}/",
                            'image_link': f"https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/{appid}/capsule_231x87.jpg",
                        }
                        
                        # Check if we already have this game
                        if not any(g['appid'] == appid for g in games):
                            games.append(game_data)
                            logger.debug(f"  Found via regex: {name} (AppID: {appid})")
            
            logger.info(f"Simple regex parsing found {len(games)} games")
            
            # If regex found games, use them
            if games:
                return games
            
            # If not, fall back to original method
            return self._parse_games_from_current_page()
            
        except Exception as e:
            logger.error(f"Error in simple parsing: {e}")
            return self._parse_games_from_current_page()
    
    def _extract_game_data_from_row(self, row_element) -> Optional[Dict]:
        """Extract game data from a table row using Selenium"""
        try:
            # Get the entire row HTML to understand structure
            row_html = row_element.get_attribute('outerHTML')
            
            # Try multiple selectors for game link
            app_link = None
            selectors = [
                'td:nth-child(2) a[href^="/app/"]',
                'td a.b[href^="/app/"]',  # class="b" for bold
                'td a[href^="/app/"]',
                'a[href^="/app/"]',  # Direct a tag
                'td a[title]',  # Sometimes has title attribute
            ]
            
            for selector in selectors:
                try:
                    app_link = row_element.find_element(By.CSS_SELECTOR, selector)
                    if app_link:
                        break
                except NoSuchElementException:
                    continue
            
            if not app_link:
                # Try to find any link with app in it
                try:
                    all_links = row_element.find_elements(By.TAG_NAME, 'a')
                    for link in all_links:
                        href = link.get_attribute('href') or ''
                        if '/app/' in href:
                            app_link = link
                            break
                except:
                    pass
            
            if not app_link:
                logger.debug("No app link found in row")
                return None
            
            # Get name and href
            name = app_link.text.strip()
            href = app_link.get_attribute('href')
            
            # If name is empty, try to get it from title attribute
            if not name:
                name = app_link.get_attribute('title') or ''
                name = name.strip()
            
            # Extract appid from href
            appid_match = re.search(r'/app/(\d+)', href)
            if not appid_match:
                # Try to find appid in data attributes or other places
                appid_match = re.search(r'appid[=:](\d+)', row_html.lower())
                if not appid_match:
                    return None
            
            appid = appid_match.group(1)
            
            if not name or not appid:
                logger.debug(f"Missing name or appid: name='{name}', appid='{appid}'")
                return None
            
            # Steam store URL
            steam_link = f"https://store.steampowered.com/app/{appid}/"
            
            # Try to get store link from store icon
            try:
                store_links = row_element.find_elements(By.CSS_SELECTOR, 'a[title*="Store"], a[title*="Steam"], a.info-icon')
                for store_link in store_links:
                    store_href = store_link.get_attribute('href')
                    if store_href and 'steampowered.com' in store_href:
                        steam_link = store_href.split('?')[0]
                        break
            except NoSuchElementException:
                pass
            
            # Image URL
            image_link = f"https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/{appid}/capsule_231x87.jpg"
            try:
                # Try multiple image selectors
                img_selectors = [
                    'img[src*="capsule"]',
                    'img[src*="header"]',
                    'img[data-c]',  # Data attribute
                    'td:nth-child(1) img',  # First column usually has image
                    'img'  # Any image
                ]
                
                for selector in img_selectors:
                    try:
                        img = row_element.find_element(By.CSS_SELECTOR, selector)
                        src = img.get_attribute('src')
                        if src:
                            image_link = src if src.startswith('http') else f"https:{src}"
                            break
                    except:
                        continue
            except:
                pass
            
            # Additional info - try to get from data attributes
            additional_info = {}
            
            # Get all cells to find data
            try:
                cells = row_element.find_elements(By.TAG_NAME, 'td')
                for i, cell in enumerate(cells):
                    cell_text = cell.text.strip()
                    cell_html = cell.get_attribute('innerHTML')
                    
                    # Check for release date (often has data-s="release" or contains date)
                    if 'data-s="release"' in cell_html or (cell_text and re.match(r'\d{4}-\d{2}-\d{2}', cell_text)):
                        additional_info['release_date'] = cell_text
                    
                    # Check for reviews
                    if 'data-s="reviews"' in cell_html or ('reviews' in cell_html.lower() and cell_text.replace(',', '').replace('.', '').isdigit()):
                        additional_info['reviews'] = cell_text
                    
                    # Check for positive percentage
                    if 'data-s="positive"' in cell_html or ('%' in cell_text and 'positive' in cell_html.lower()):
                        additional_info['positive_percentage'] = cell_text
            
            except:
                pass
            
            # Tags
            tags = []
            try:
                # Look for tag links
                tag_elements = row_element.find_elements(By.CSS_SELECTOR, 'a[href^="/tag/"], a.tag')
                for tag in tag_elements:
                    tag_text = tag.text.strip()
                    if tag_text:
                        tags.append(tag_text)
                
                # Also check for text that looks like tags
                row_text = row_element.text
                if 'Indie' in row_text or 'Action' in row_text or 'Adventure' in row_text:
                    # Extract common tags from text
                    common_tags = ['Indie', 'Action', 'Adventure', 'RPG', 'Strategy', 'Casual', 
                                  'Simulation', 'Sports', 'Racing', 'Massively Multiplayer']
                    for tag in common_tags:
                        if tag in row_text and tag not in tags:
                            tags.append(tag)
            
            except:
                pass
            
            if tags:
                additional_info['tags'] = tags
            
            # Get SteamDB link
            steamdb_link = f"https://steamdb.info/app/{appid}/"
            
            game_data = {
                'appid': appid,
                'name': name,
                'steam_link': steam_link,
                'steamdb_link': steamdb_link,
                'image_link': image_link,
                **additional_info
            }
            
            logger.debug(f"Successfully parsed game: {name} (AppID: {appid})")
            return game_data
        
        except NoSuchElementException:
            logger.debug("NoSuchElementException in row extraction")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in row extraction: {e}")
            logger.debug(f"Row HTML: {row_element.get_attribute('outerHTML')[:500]}")
            return None
    
    def generate_json_output(self, categories: Dict, output_file: str = 'steamdb_selenium.json'):
        """Generate JSON output"""
        output_data = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'source': 'SteamDB',
                'base_url': self.base_url,
                'method': 'selenium_with_ajax_fallback',
                'total_categories': len(categories),
                'total_technologies': sum(len(techs) for techs in categories.values()),
                'total_games': sum(len(tech.get('games', [])) for category in categories.values() for tech in category.values())
            },
            'technologies': categories
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Data saved to {output_file}")
        
        print("\n" + "="*60)
        print("PARSING SUMMARY")
        print("="*60)
        print(f"Output file: {output_file}")
        print(f"Total categories: {output_data['metadata']['total_categories']}")
        print(f"Total technologies: {output_data['metadata']['total_technologies']}")
        print(f"Total games collected: {output_data['metadata']['total_games']}")
        
        print("\nGames per technology:")
        for cat_name, techs in categories.items():
            for tech_name, tech_info in techs.items():
                if tech_info.get('games'):
                    print(f"  {cat_name}/{tech_name}: {len(tech_info['games'])} games")
        print("="*60)
        
        return output_data
    
    def close(self):
        """Close the browser"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Browser closed")
            except:
                logger.warning("Error closing browser")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Parse SteamDB using Selenium')
    parser.add_argument('--headless', action='store_true', help='Run browser in headless mode')
    parser.add_argument('--min-count', type=int, default=1000, help='Minimum game count for technology')
    parser.add_argument('--min-reviews', type=int, default=500, help='Minimum reviews for games')
    parser.add_argument('--max-pages', type=int, default=100, help='Max pages per technology (set high for all pages)')
    parser.add_argument('--output', type=str, default='steamdb_selenium.json', help='Output file')
    parser.add_argument('--test', action='store_true', help='Test mode - only fetch categories')
    parser.add_argument('--categories', type=str, default='Engine', help='Categories to scrape (comma-separated)')
    parser.add_argument('--limit-tech', type=int, default=5, help='Limit number of technologies per category')
    
    args = parser.parse_args()
    
    print("="*60)
    print("STEAMDB SELENIUM PARSER (WITH AJAX OPTIMIZATION)")
    print("="*60)
    print(f"Headless mode: {args.headless}")
    print(f"Test mode: {args.test}")
    print(f"Output file: {args.output}")
    print(f"Categories: {args.categories}")
    print(f"Limit technologies per category: {args.limit_tech}")
    print(f"Max pages per technology: {args.max_pages}")
    print("="*60)
    print("\nNote: This will try AJAX method first, fall back to Selenium if needed.")
    print("It will open a Chrome browser window and handle Cloudflare challenges.")
    print("="*60)
    
    if not HAS_SELENIUM:
        print("\nERROR: Required packages not installed!")
        print("Please install: pip install selenium webdriver-manager beautifulsoup4 requests")
        return
    
    parser_obj = None
    try:
        parser_obj = SteamDBSeleniumParser(headless=args.headless)
        
        print("\nSetting up Chrome browser...")
        if not parser_obj.setup_driver():
            print("Failed to setup ChromeDriver. Exiting.")
            return
        
        print("\nFetching technology categories...")
        categories = parser_obj.get_all_technologies()
        
        if not categories:
            print("\nNo categories found. Check the screenshots and logs.")
            print("Check saved files: tech_categories.png, current_page.html")
            return
        
        target_categories = args.categories.split(',')
        categories = {k: v for k, v in categories.items() if k in target_categories}
        
        if not categories:
            print(f"\nNo matching categories found from: {target_categories}")
            print(f"Available categories: {list(categories.keys())}")
            return
        
        if not args.test:
            print("\nFetching games for technologies...")
            for cat_name, techs in categories.items():
                print(f"\nProcessing {cat_name} category:")
                
                sorted_techs = sorted(
                    techs.items(), 
                    key=lambda x: x[1]['count'], 
                    reverse=True
                )[:args.limit_tech]
                
                for tech_name, tech_info in sorted_techs:
                    if tech_info['count'] < args.min_count:
                        print(f"  Skipping {tech_name} (count: {tech_info['count']} < {args.min_count})")
                        continue
                    
                    print(f"  Fetching games for {tech_name} ({tech_info['count']} games total)...")
                    try:
                        games = parser_obj.get_games_for_technology(
                            tech_info['link'],
                            tech_name,
                            min_reviews=args.min_reviews,
                            max_pages=args.max_pages
                        )
                        tech_info['games'] = games
                        print(f"    Found {len(games)} games (after filters)")
                        
                        if games:
                            print(f"    First 3 games:")
                            for i, game in enumerate(games[:3]):
                                print(f"      {i+1}. {game['name']} (AppID: {game['appid']})")
                        
                        time.sleep(3)  # Be nice to the server
                        
                    except Exception as e:
                        print(f"    Error fetching games: {e}")
                        tech_info['games'] = []
                        tech_info['error'] = str(e)
        
        print(f"\nGenerating output: {args.output}")
        parser_obj.generate_json_output(categories, args.output)
        
        print("\n" + "="*60)
        print("PARSING COMPLETE!")
        print("="*60)
        print(f"Output saved to: {args.output}")
        print(f"Log file: steamdb_selenium.log")
        print(f"Debug files saved:")
        print(f"  - tech_categories.png (screenshot of categories page)")
        print(f"  - current_page.html (HTML of last page visited)")
        print(f"  - debug_*.html (debug HTML for specific pages)")
        print("="*60)
        
    except KeyboardInterrupt:
        print("\n\nParser interrupted by user.")
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if parser_obj and parser_obj.driver:
            print("\nClosing browser...")
            parser_obj.close()


if __name__ == "__main__":
    main()