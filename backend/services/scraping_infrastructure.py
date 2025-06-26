"""
Enhanced Web Scraping Infrastructure with Advanced Anti-Detection Measures
"""

import asyncio
import logging
import random
import time
import json
from typing import Dict, List, Optional, Any, Union
from urllib.parse import urlparse
from datetime import datetime
from pathlib import Path

try:
    import undetected_chromedriver as uc
except ImportError:
    uc = None

try:
    from fake_useragent import UserAgent
except ImportError:
    UserAgent = None

try:
    from selenium_stealth import stealth
except ImportError:
    stealth = None

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.action_chains import ActionChains

logger = logging.getLogger(__name__)


class CaptchaDetectedError(Exception):
    """Raised when a CAPTCHA is detected"""
    pass


class ProxyRotator:
    """Handles proxy rotation for anti-detection"""
    
    def __init__(self, proxy_list: Optional[List[str]] = None):
        self.proxy_list = proxy_list or []
        self.current_index = 0
        
    def get_next_proxy(self) -> Optional[str]:
        """Get the next proxy in rotation"""
        if not self.proxy_list:
            return None
            
        proxy = self.proxy_list[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.proxy_list)
        return proxy
        
    def add_proxy(self, proxy: str):
        """Add a proxy to the rotation list"""
        if proxy not in self.proxy_list:
            self.proxy_list.append(proxy)


class UserAgentRotator:
    """Enhanced user agent rotation with fake-useragent library"""
    
    def __init__(self):
        self.ua = UserAgent() if UserAgent else None
        self.custom_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:123.0) Gecko/20100101 Firefox/123.0",
        ]
        
    def get_random_user_agent(self) -> str:
        """Get a random user agent"""
        if self.ua and random.random() < 0.7:  # 70% chance to use fake-useragent
            try:
                return self.ua.random
            except Exception:
                pass  # Fallback to custom agents
        return random.choice(self.custom_agents)


class BehaviorSimulator:
    """Simulates human-like behavior"""
    
    def __init__(self, driver: webdriver.Chrome):
        self.driver = driver
        self.action_chains = ActionChains(driver)
        
    async def random_mouse_movement(self):
        """Simulate random mouse movements"""
        try:
            body = self.driver.find_element(By.TAG_NAME, "body")
            width = self.driver.get_window_size()["width"]
            height = self.driver.get_window_size()["height"]
            
            # Random mouse movements
            for _ in range(random.randint(1, 3)):
                x = random.randint(0, width)
                y = random.randint(0, height)
                self.action_chains.move_by_offset(x, y).perform()
                await asyncio.sleep(random.uniform(0.1, 0.5))
                
        except Exception as e:
            logger.debug(f"Mouse movement simulation failed: {e}")
            
    async def random_scroll(self):
        """Simulate random scrolling"""
        try:
            # Scroll to random positions
            scroll_positions = [
                random.randint(0, 500),
                random.randint(500, 1000),
                random.randint(1000, 2000)
            ]
            
            for position in scroll_positions:
                self.driver.execute_script(f"window.scrollTo(0, {position});")
                await asyncio.sleep(random.uniform(0.5, 2.0))
                
        except Exception as e:
            logger.debug(f"Scroll simulation failed: {e}")
            
    async def simulate_reading_delay(self):
        """Simulate human reading time"""
        delay = random.uniform(2.0, 8.0)
        await asyncio.sleep(delay)


class CaptchaDetector:
    """Detects various types of CAPTCHAs"""
    
    CAPTCHA_INDICATORS = [
        "captcha",
        "recaptcha", 
        "hcaptcha",
        "I'm not a robot",
        "verify you are human",
        "prove you are not a robot",
        "security check",
        "unusual traffic"
    ]
    
    CAPTCHA_SELECTORS = [
        "iframe[src*='recaptcha']",
        "iframe[src*='hcaptcha']", 
        ".g-recaptcha",
        ".h-captcha",
        "#captcha",
        ".captcha",
        "[data-sitekey]"
    ]
    
    def __init__(self, driver: webdriver.Chrome):
        self.driver = driver
        
    def detect_captcha(self) -> bool:
        """Detect if a CAPTCHA is present on the page"""
        try:
            # Check page source for captcha indicators
            page_source = self.driver.page_source.lower()
            for indicator in self.CAPTCHA_INDICATORS:
                if indicator in page_source:
                    logger.warning(f"CAPTCHA detected: {indicator}")
                    return True
                    
            # Check for captcha elements
            for selector in self.CAPTCHA_SELECTORS:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if element.is_displayed():
                        logger.warning(f"CAPTCHA element detected: {selector}")
                        return True
                except:
                    continue
                    
            return False
            
        except Exception as e:
            logger.debug(f"CAPTCHA detection failed: {e}")
            return False


class RequestThrottler:
    """Handles request throttling with exponential backoff"""
    
    def __init__(self, base_delay: float = 2.0, max_delay: float = 60.0):
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.current_delay = base_delay
        self.last_request_time = 0
        
    async def wait(self):
        """Wait before making next request"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.current_delay:
            wait_time = self.current_delay - time_since_last
            # Add randomization
            wait_time += random.uniform(0.5, 2.0)
            await asyncio.sleep(wait_time)
            
        self.last_request_time = time.time()
        
    def increase_delay(self):
        """Increase delay after errors (exponential backoff)"""
        self.current_delay = min(self.current_delay * 2, self.max_delay)
        logger.info(f"Increased request delay to {self.current_delay}s")
        
    def reset_delay(self):
        """Reset delay after successful requests"""
        self.current_delay = self.base_delay


class AntiDetectionScraper:
    """Main scraping class with comprehensive anti-detection measures"""
    
    def __init__(
        self,
        headless: bool = True,
        proxy_list: Optional[List[str]] = None,
        user_data_dir: Optional[str] = None,
        enable_stealth: bool = True,
        request_delay: float = 3.0
    ):
        self.headless = headless
        self.proxy_rotator = ProxyRotator(proxy_list)
        self.ua_rotator = UserAgentRotator()
        self.enable_stealth = enable_stealth
        self.user_data_dir = user_data_dir
        self.driver: Optional[webdriver.Chrome] = None
        self.behavior_simulator: Optional[BehaviorSimulator] = None
        self.captcha_detector: Optional[CaptchaDetector] = None
        self.throttler = RequestThrottler(base_delay=request_delay)
        self._session_cookies: Dict[str, Any] = {}
        
    def _create_chrome_options(self) -> ChromeOptions:
        """Create Chrome options with advanced anti-detection"""
        options = ChromeOptions()
        
        # Basic stealth options
        if self.headless:
            options.add_argument("--headless=new")
        
        # Window size randomization
        width = random.randint(1366, 1920)
        height = random.randint(768, 1080)
        options.add_argument(f"--window-size={width},{height}")
        
        # Core anti-detection arguments
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Additional stealth measures
        options.add_argument("--disable-web-security")
        options.add_argument("--disable-features=VizDisplayCompositor")
        options.add_argument("--disable-background-timer-throttling")
        options.add_argument("--disable-backgrounding-occluded-windows")
        options.add_argument("--disable-renderer-backgrounding")
        options.add_argument("--disable-field-trial-config")
        
        # Proxy setup
        proxy = self.proxy_rotator.get_next_proxy()
        if proxy:
            options.add_argument(f"--proxy-server={proxy}")
        
        # User agent
        user_agent = self.ua_rotator.get_random_user_agent()
        options.add_argument(f"--user-agent={user_agent}")
        
        # User data directory
        if self.user_data_dir:
            options.add_argument(f"--user-data-dir={self.user_data_dir}")
        
        # Enhanced preferences for stealth
        prefs = {
            "profile.default_content_setting_values": {
                "notifications": 2,
                "media_stream": 2,
                "geolocation": 2,
            },
            "profile.managed_default_content_settings": {
                "images": 1  # Allow images for better stealth
            }
        }
        options.add_experimental_option("prefs", prefs)
        
        return options
        
    async def create_driver(self) -> webdriver.Chrome:
        """Create driver with anti-detection measures"""
        try:
            options = self._create_chrome_options()
            
            # Try undetected-chromedriver first
            if uc:
                self.driver = uc.Chrome(
                    options=options,
                    version_main=None,  # Auto-detect Chrome version
                )
                logger.info("Created undetected Chrome driver")
            else:
                # Fallback to regular ChromeDriver
                from webdriver_manager.chrome import ChromeDriverManager
                from selenium.webdriver.chrome.service import Service
                
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=options)
                logger.info("Created regular Chrome driver")
            
            # Apply selenium-stealth if available
            if stealth and self.enable_stealth:
                stealth(
                    self.driver,
                    languages=["en-US", "en"],
                    vendor="Google Inc.",
                    platform="Win32",
                    webgl_vendor="Intel Inc.",
                    renderer="Intel Iris OpenGL Engine",
                    fix_hairline=True,
                )
                logger.info("Applied selenium-stealth")
            
            # Initialize helper classes
            self.behavior_simulator = BehaviorSimulator(self.driver)
            self.captcha_detector = CaptchaDetector(self.driver)
            
            # Apply additional anti-detection scripts
            await self._apply_anti_detection_scripts()
            
            return self.driver
            
        except Exception as e:
            logger.error(f"Failed to create driver: {str(e)}")
            raise WebDriverException(f"Failed to create driver: {str(e)}")
    
    async def _apply_anti_detection_scripts(self):
        """Apply additional JavaScript-based anti-detection measures"""
        if not self.driver:
            return
            
        try:
            # Remove webdriver property
            self.driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            
            # Mock plugins
            self.driver.execute_script("""
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
            """)
            
            # Mock languages
            self.driver.execute_script("""
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
            """)
            
            # Mock chrome runtime
            self.driver.execute_script("""
                window.chrome = {
                    runtime: {}
                };
            """)
            
        except Exception as e:
            logger.debug(f"Anti-detection script application failed: {e}")
            
    async def get_page_with_stealth(self, url: str, wait_time: float = 5.0) -> str:
        """Get page content with full anti-detection measures"""
        if not self.driver:
            await self.create_driver()
            
        try:
            # Apply request throttling
            await self.throttler.wait()
            
            # Navigate to page
            self.driver.get(url)
            
            # Wait for page load
            WebDriverWait(self.driver, wait_time).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Check for CAPTCHA
            if self.captcha_detector and self.captcha_detector.detect_captcha():
                self.throttler.increase_delay()
                raise CaptchaDetectedError(f"CAPTCHA detected on {url}")
            
            # Simulate human behavior
            if self.behavior_simulator:
                await self.behavior_simulator.random_mouse_movement()
                await self.behavior_simulator.random_scroll()
                await self.behavior_simulator.simulate_reading_delay()
            
            # Reset delay on success
            self.throttler.reset_delay()
            
            return self.driver.page_source
            
        except TimeoutException:
            self.throttler.increase_delay()
            raise WebDriverException(f"Page load timeout for {url}")
        except Exception as e:
            self.throttler.increase_delay()
            logger.error(f"Error getting page {url}: {str(e)}")
            raise
            
    def quit(self):
        """Clean up driver resources"""
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                logger.debug(f"Error quitting driver: {e}")
            finally:
                self.driver = None
                
    async def __aenter__(self):
        await self.create_driver()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.quit()


class SessionManager:
    """Manages persistent sessions and cookies"""
    
    def __init__(self, session_file: Optional[str] = None):
        self.session_file = session_file or "session_data.json"
        self.session_data: Dict[str, Any] = {}
        self.load_session()
        
    def load_session(self):
        """Load session data from file"""
        try:
            if Path(self.session_file).exists():
                with open(self.session_file, 'r') as f:
                    self.session_data = json.load(f)
                logger.info(f"Loaded session data from {self.session_file}")
        except Exception as e:
            logger.warning(f"Failed to load session data: {e}")
            self.session_data = {}
            
    def save_session(self):
        """Save session data to file"""
        try:
            with open(self.session_file, 'w') as f:
                json.dump(self.session_data, f, indent=2)
            logger.info(f"Saved session data to {self.session_file}")
        except Exception as e:
            logger.error(f"Failed to save session data: {e}")
            
    def set_cookies(self, driver: webdriver.Chrome, domain: str):
        """Set stored cookies for a domain"""
        if domain in self.session_data.get('cookies', {}):
            try:
                driver.get(f"https://{domain}")  # Navigate to domain first
                for cookie in self.session_data['cookies'][domain]:
                    driver.add_cookie(cookie)
                logger.info(f"Set {len(self.session_data['cookies'][domain])} cookies for {domain}")
            except Exception as e:
                logger.warning(f"Failed to set cookies for {domain}: {e}")
                
    def save_cookies(self, driver: webdriver.Chrome, domain: str):
        """Save cookies for a domain"""
        try:
            cookies = driver.get_cookies()
            if 'cookies' not in self.session_data:
                self.session_data['cookies'] = {}
            self.session_data['cookies'][domain] = cookies
            self.save_session()
            logger.info(f"Saved {len(cookies)} cookies for {domain}")
        except Exception as e:
            logger.error(f"Failed to save cookies for {domain}: {e}")


# Factory function for easy instantiation
async def create_stealth_scraper(
    headless: bool = True,
    proxy_list: Optional[List[str]] = None,
    session_file: Optional[str] = None,
    request_delay: float = 3.0
) -> AntiDetectionScraper:
    """Factory function to create a configured stealth scraper"""
    scraper = AntiDetectionScraper(
        headless=headless,
        proxy_list=proxy_list,
        request_delay=request_delay
    )
    await scraper.create_driver()
    return scraper
