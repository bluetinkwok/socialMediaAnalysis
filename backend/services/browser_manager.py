"""
Browser Manager - Handles Selenium WebDriver with anti-detection measures
"""

import asyncio
import logging
import random
import tempfile
import os
from typing import Optional, Dict, Any
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.common.exceptions import WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager

logger = logging.getLogger(__name__)


class BrowserManager:
    """
    Manages browser instances with anti-detection measures and optimal configuration
    """
    
    def __init__(
        self,
        browser_type: str = "chrome",
        headless: bool = True,
        window_size: tuple = (1920, 1080),
        user_data_dir: Optional[str] = None
    ):
        self.browser_type = browser_type.lower()
        self.headless = headless
        self.window_size = window_size
        self.user_data_dir = user_data_dir or self._create_temp_profile()
        self.driver: Optional[webdriver.Remote] = None
        self._driver_lock = asyncio.Lock()
        
        # Anti-detection configurations
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) Gecko/20100101 Firefox/122.0"
        ]
        
    def _create_temp_profile(self) -> str:
        """Create a temporary profile directory"""
        temp_dir = tempfile.mkdtemp(prefix="browser_profile_")
        return temp_dir
        
    def _get_chrome_options(self) -> ChromeOptions:
        """Configure Chrome options with anti-detection measures"""
        options = ChromeOptions()
        
        # Basic options
        if self.headless:
            options.add_argument("--headless=new")
        options.add_argument(f"--window-size={self.window_size[0]},{self.window_size[1]}")
        options.add_argument(f"--user-data-dir={self.user_data_dir}")
        
        # Anti-detection measures
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Performance optimizations
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins")
        options.add_argument("--disable-images")
        # JavaScript is needed for Threads content loading
        # options.add_argument("--disable-javascript")  # Disabled for dynamic content
        options.add_argument("--disable-css")
        
        # Privacy and security
        options.add_argument("--disable-web-security")
        options.add_argument("--disable-features=VizDisplayCompositor")
        options.add_argument("--disable-background-timer-throttling")
        options.add_argument("--disable-backgrounding-occluded-windows")
        options.add_argument("--disable-renderer-backgrounding")
        
        # Random user agent
        user_agent = random.choice(self.user_agents)
        options.add_argument(f"--user-agent={user_agent}")
        
        # Additional preferences
        prefs = {
            "profile.default_content_setting_values": {
                "notifications": 2,
                "media_stream": 2,
            },
            "profile.managed_default_content_settings": {
                "images": 2
            }
        }
        options.add_experimental_option("prefs", prefs)
        
        return options
        
    def _get_firefox_options(self) -> FirefoxOptions:
        """Configure Firefox options with anti-detection measures"""
        options = FirefoxOptions()
        
        # Basic options
        if self.headless:
            options.add_argument("--headless")
        options.add_argument(f"--width={self.window_size[0]}")
        options.add_argument(f"--height={self.window_size[1]}")
        
        # Performance optimizations
        options.set_preference("permissions.default.image", 2)  # Block images
        options.set_preference("dom.ipc.plugins.enabled.libflashplayer.so", False)
        options.set_preference("media.volume_scale", "0.0")
        
        # Privacy settings
        options.set_preference("privacy.trackingprotection.enabled", True)
        options.set_preference("dom.webnotifications.enabled", False)
        options.set_preference("media.navigator.enabled", False)
        
        # Random user agent
        user_agent = random.choice(self.user_agents)
        options.set_preference("general.useragent.override", user_agent)
        
        return options
        
    async def get_driver(self) -> webdriver.Remote:
        """Get or create a WebDriver instance"""
        async with self._driver_lock:
            if self.driver is None:
                await self._create_driver()
            return self.driver
            
    async def _create_driver(self):
        """Create a new WebDriver instance"""
        try:
            if self.browser_type == "chrome":
                options = self._get_chrome_options()
                
                # Use ChromeDriverManager to automatically get the correct version
                # This ensures ChromeDriver version matches the installed Chrome browser
                driver_path = ChromeDriverManager().install()
                # Ensure we get the actual chromedriver executable, not other files
                if os.path.basename(driver_path) != 'chromedriver':
                    driver_dir = os.path.dirname(driver_path)
                    actual_driver = os.path.join(driver_dir, 'chromedriver')
                    if os.path.exists(actual_driver):
                        driver_path = actual_driver
                service = ChromeService(driver_path)
                logger.info(f"Using managed chromedriver: {driver_path}")
                
                self.driver = webdriver.Chrome(service=service, options=options)
            elif self.browser_type == "firefox":
                options = self._get_firefox_options()
                service = FirefoxService(GeckoDriverManager().install())
                self.driver = webdriver.Firefox(service=service, options=options)
            else:
                raise ValueError(f"Unsupported browser type: {self.browser_type}")
                
            # Execute anti-detection script
            await self._setup_anti_detection()
            
            logger.info(f"Created {self.browser_type} WebDriver instance")
            
        except Exception as e:
            logger.error(f"Failed to create WebDriver: {str(e)}")
            raise WebDriverException(f"Failed to create {self.browser_type} driver: {str(e)}")
            
    async def _setup_anti_detection(self):
        """Setup anti-detection measures"""
        if not self.driver:
            return
            
        # Chrome-specific anti-detection
        if self.browser_type == "chrome":
            # Remove webdriver property
            self.driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            
            # Override plugins length
            self.driver.execute_script(
                "Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})"
            )
            
            # Override languages
            self.driver.execute_script(
                "Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']})"
            )
            
        # Set random viewport size (slight variation)
        width_offset = random.randint(-50, 50)
        height_offset = random.randint(-50, 50)
        new_width = max(800, self.window_size[0] + width_offset)
        new_height = max(600, self.window_size[1] + height_offset)
        
        self.driver.set_window_size(new_width, new_height)
        
    async def restart_driver(self):
        """Restart the WebDriver instance"""
        async with self._driver_lock:
            if self.driver:
                try:
                    self.driver.quit()
                except Exception as e:
                    logger.warning(f"Error quitting driver: {str(e)}")
                finally:
                    self.driver = None
                    
            await self._create_driver()
            
    def quit(self):
        """Quit the WebDriver and clean up resources"""
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                logger.warning(f"Error quitting driver: {str(e)}")
            finally:
                self.driver = None
                
        # Clean up temporary profile directory
        if self.user_data_dir and os.path.exists(self.user_data_dir):
            try:
                import shutil
                shutil.rmtree(self.user_data_dir)
            except Exception as e:
                logger.warning(f"Error cleaning up profile directory: {str(e)}")
                
    async def get_page_source(self, url: str, wait_time: float = 2.0) -> str:
        """Get page source with optional wait time"""
        driver = await self.get_driver()
        driver.get(url)
        
        # Wait for page to load
        await asyncio.sleep(wait_time)
        
        # Random human-like behavior
        if random.random() < 0.3:
            # Random scroll
            scroll_height = random.randint(100, 500)
            driver.execute_script(f"window.scrollBy(0, {scroll_height});")
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
        return driver.page_source
        
    async def execute_script(self, script: str) -> Any:
        """Execute JavaScript in the browser"""
        driver = await self.get_driver()
        return driver.execute_script(script)
        
    async def get_cookies(self) -> Dict[str, Any]:
        """Get all cookies from the current session"""
        driver = await self.get_driver()
        return {cookie['name']: cookie['value'] for cookie in driver.get_cookies()}
        
    async def set_cookies(self, cookies: Dict[str, str]):
        """Set cookies in the browser"""
        driver = await self.get_driver()
        for name, value in cookies.items():
            driver.add_cookie({'name': name, 'value': value})
            
    def get_browser_info(self) -> Dict[str, Any]:
        """Get information about the browser configuration"""
        return {
            'browser_type': self.browser_type,
            'headless': self.headless,
            'window_size': self.window_size,
            'user_data_dir': self.user_data_dir,
            'is_active': self.driver is not None
        } 