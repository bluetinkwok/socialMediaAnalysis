"""
Test suite for enhanced web scraping infrastructure (fixed version)
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.common.exceptions import WebDriverException, TimeoutException

from services.scraping_infrastructure import (
    AntiDetectionScraper,
    ProxyRotator,
    UserAgentRotator,
    BehaviorSimulator,
    CaptchaDetector,
    RequestThrottler,
    SessionManager,
    CaptchaDetectedError,
    create_stealth_scraper
)


class TestProxyRotator:
    """Test proxy rotation functionality"""
    
    def test_init_empty(self):
        rotator = ProxyRotator()
        assert rotator.proxy_list == []
        assert rotator.current_index == 0
        
    def test_init_with_proxies(self):
        proxies = ["proxy1:8080", "proxy2:8080"]
        rotator = ProxyRotator(proxies)
        assert rotator.proxy_list == proxies
        
    def test_get_next_proxy_empty_list(self):
        rotator = ProxyRotator()
        assert rotator.get_next_proxy() is None
        
    def test_get_next_proxy_rotation(self):
        proxies = ["proxy1:8080", "proxy2:8080", "proxy3:8080"]
        rotator = ProxyRotator(proxies)
        
        # Test rotation
        assert rotator.get_next_proxy() == "proxy1:8080"
        assert rotator.get_next_proxy() == "proxy2:8080"
        assert rotator.get_next_proxy() == "proxy3:8080"
        assert rotator.get_next_proxy() == "proxy1:8080"  # Back to start
        
    def test_add_proxy(self):
        rotator = ProxyRotator()
        rotator.add_proxy("new_proxy:8080")
        assert "new_proxy:8080" in rotator.proxy_list
        
        # Test duplicate prevention
        rotator.add_proxy("new_proxy:8080")
        assert rotator.proxy_list.count("new_proxy:8080") == 1


class TestUserAgentRotator:
    """Test user agent rotation"""
    
    def test_init(self):
        rotator = UserAgentRotator()
        assert rotator.custom_agents is not None
        assert len(rotator.custom_agents) > 0
        
    def test_get_random_user_agent(self):
        rotator = UserAgentRotator()
        ua1 = rotator.get_random_user_agent()
        ua2 = rotator.get_random_user_agent()
        
        assert isinstance(ua1, str)
        assert isinstance(ua2, str)
        assert len(ua1) > 0
        assert len(ua2) > 0


class TestBehaviorSimulator:
    """Test human behavior simulation"""
    
    @pytest.fixture
    def mock_driver(self):
        driver = Mock()
        driver.find_element.return_value = Mock()
        driver.get_window_size.return_value = {"width": 1920, "height": 1080}
        return driver
        
    def test_init(self, mock_driver):
        simulator = BehaviorSimulator(mock_driver)
        assert simulator.driver == mock_driver
        assert simulator.action_chains is not None
        
    @pytest.mark.asyncio
    async def test_random_mouse_movement(self, mock_driver):
        simulator = BehaviorSimulator(mock_driver)
        
        # Should not raise exception
        await simulator.random_mouse_movement()
        
    @pytest.mark.asyncio
    async def test_random_scroll(self, mock_driver):
        simulator = BehaviorSimulator(mock_driver)
        
        # Should not raise exception
        await simulator.random_scroll()
        
    @pytest.mark.asyncio
    async def test_simulate_reading_delay(self, mock_driver):
        simulator = BehaviorSimulator(mock_driver)
        
        import time
        start = time.time()
        await simulator.simulate_reading_delay()
        end = time.time()
        
        # Should take at least 1 second (minimum delay with tolerance)
        assert end - start >= 0.8  # More reasonable tolerance


class TestCaptchaDetector:
    """Test CAPTCHA detection"""
    
    @pytest.fixture
    def mock_driver(self):
        driver = Mock()
        return driver
        
    def test_init(self, mock_driver):
        detector = CaptchaDetector(mock_driver)
        assert detector.driver == mock_driver
        
    def test_detect_captcha_in_source(self, mock_driver):
        mock_driver.page_source = "This page has a recaptcha challenge"
        detector = CaptchaDetector(mock_driver)
        
        assert detector.detect_captcha() is True
        
    def test_detect_no_captcha(self, mock_driver):
        mock_driver.page_source = "Normal page content without any challenges"
        mock_driver.find_element.side_effect = Exception("Element not found")
        
        detector = CaptchaDetector(mock_driver)
        assert detector.detect_captcha() is False
        
    def test_detect_captcha_element(self, mock_driver):
        mock_driver.page_source = "Normal page content"
        
        # Mock finding a captcha element
        mock_element = Mock()
        mock_element.is_displayed.return_value = True
        mock_driver.find_element.return_value = mock_element
        
        detector = CaptchaDetector(mock_driver)
        
        # Should detect captcha element
        assert detector.detect_captcha() is True


class TestRequestThrottler:
    """Test request throttling"""
    
    def test_init(self):
        throttler = RequestThrottler(base_delay=1.0, max_delay=10.0)
        assert throttler.base_delay == 1.0
        assert throttler.max_delay == 10.0
        assert throttler.current_delay == 1.0
        
    @pytest.mark.asyncio
    async def test_wait_timing(self):
        throttler = RequestThrottler(base_delay=0.05)  # Very short delay for testing
        
        import time
        start = time.time()
        await throttler.wait()
        end = time.time()
        
        # Should wait at least half the base delay (tolerance for execution time)
        assert end - start >= 0.02
        
    def test_increase_delay(self):
        throttler = RequestThrottler(base_delay=2.0, max_delay=16.0)
        
        initial_delay = throttler.current_delay
        throttler.increase_delay()
        assert throttler.current_delay == initial_delay * 2
        
        # Test max delay cap
        throttler.current_delay = 16.0
        throttler.increase_delay()
        assert throttler.current_delay == 16.0  # Should not exceed max
        
    def test_reset_delay(self):
        throttler = RequestThrottler(base_delay=2.0)
        throttler.current_delay = 8.0
        
        throttler.reset_delay()
        assert throttler.current_delay == 2.0


class TestAntiDetectionScraper:
    """Test the main scraper class"""
    
    def test_init(self):
        scraper = AntiDetectionScraper()
        assert scraper.headless is True
        assert scraper.proxy_rotator is not None
        assert scraper.ua_rotator is not None
        assert scraper.driver is None
        
    def test_init_with_params(self):
        proxy_list = ["proxy1:8080", "proxy2:8080"]
        scraper = AntiDetectionScraper(
            headless=False,
            proxy_list=proxy_list,
            request_delay=5.0
        )
        
        assert scraper.headless is False
        assert scraper.proxy_rotator.proxy_list == proxy_list
        assert scraper.throttler.base_delay == 5.0
        
    def test_create_chrome_options(self):
        scraper = AntiDetectionScraper()
        options = scraper._create_chrome_options()
        
        assert isinstance(options, ChromeOptions)
        # Should have some arguments set
        assert len(options.arguments) > 0
        
    def test_create_chrome_options_with_proxy(self):
        proxy_list = ["proxy1:8080"]
        scraper = AntiDetectionScraper(proxy_list=proxy_list)
        options = scraper._create_chrome_options()
        
        # Should include proxy argument
        proxy_args = [arg for arg in options.arguments if "--proxy-server" in arg]
        assert len(proxy_args) > 0
        
    @patch('services.scraping_infrastructure.uc')
    @patch('services.scraping_infrastructure.stealth')
    @pytest.mark.asyncio
    async def test_create_driver_success(self, mock_stealth, mock_uc):
        """Test successful driver creation"""
        # Create a proper mock that passes isinstance check
        from selenium.webdriver.chrome.webdriver import WebDriver
        mock_driver = Mock(spec=WebDriver)
        mock_driver.execute_script = Mock()
        mock_uc.Chrome.return_value = mock_driver
        
        scraper = AntiDetectionScraper()
        result = await scraper.create_driver()
        
        assert result == mock_driver
        assert scraper.driver == mock_driver
        assert scraper.behavior_simulator is not None
        assert scraper.captcha_detector is not None
        
    @patch('services.scraping_infrastructure.uc', None)  # Simulate uc not available
    @patch('services.scraping_infrastructure.webdriver.Chrome')
    @patch('webdriver_manager.chrome.ChromeDriverManager')
    @pytest.mark.asyncio
    async def test_create_driver_fallback(self, mock_manager, mock_chrome):
        """Test fallback to regular ChromeDriver"""
        from selenium.webdriver.chrome.webdriver import WebDriver
        mock_driver = Mock(spec=WebDriver)
        mock_driver.execute_script = Mock()
        mock_chrome.return_value = mock_driver
        mock_manager.return_value.install.return_value = "/path/to/chromedriver"
        
        scraper = AntiDetectionScraper()
        result = await scraper.create_driver()
        
        assert result == mock_driver
        assert scraper.driver == mock_driver
        
    @patch('services.scraping_infrastructure.uc')
    @pytest.mark.asyncio
    async def test_create_driver_failure(self, mock_uc):
        """Test driver creation failure"""
        mock_uc.Chrome.side_effect = Exception("Driver creation failed")
        
        scraper = AntiDetectionScraper()
        
        with pytest.raises(WebDriverException):
            await scraper.create_driver()
            
    @patch('services.scraping_infrastructure.uc')
    @patch('services.scraping_infrastructure.WebDriverWait')
    @patch('services.scraping_infrastructure.stealth')
    @pytest.mark.asyncio
    async def test_get_page_with_stealth_success(self, mock_stealth, mock_wait, mock_uc):
        """Test successful page retrieval"""
        from selenium.webdriver.chrome.webdriver import WebDriver
        mock_driver = Mock(spec=WebDriver)
        mock_driver.get = Mock()
        mock_driver.page_source = "<html>Test content</html>"
        mock_driver.execute_script = Mock()
        mock_uc.Chrome.return_value = mock_driver
        
        # Mock wait and behavior components
        mock_wait.return_value.until.return_value = True
        
        scraper = AntiDetectionScraper()
        await scraper.create_driver()
        
        # Mock behavior simulator
        scraper.behavior_simulator = Mock()
        scraper.behavior_simulator.random_mouse_movement = AsyncMock()
        scraper.behavior_simulator.random_scroll = AsyncMock()
        scraper.behavior_simulator.simulate_reading_delay = AsyncMock()
        
        # Mock captcha detector
        scraper.captcha_detector = Mock()
        scraper.captcha_detector.detect_captcha.return_value = False
        
        result = await scraper.get_page_with_stealth("https://example.com")
        
        assert result == "<html>Test content</html>"
        mock_driver.get.assert_called_once_with("https://example.com")
        
    @patch('services.scraping_infrastructure.uc')
    @patch('services.scraping_infrastructure.stealth')
    @pytest.mark.asyncio
    async def test_get_page_captcha_detected(self, mock_stealth, mock_uc):
        """Test CAPTCHA detection during page retrieval"""
        from selenium.webdriver.chrome.webdriver import WebDriver
        mock_driver = Mock(spec=WebDriver)
        mock_driver.get = Mock()
        mock_driver.execute_script = Mock()
        mock_uc.Chrome.return_value = mock_driver
        
        scraper = AntiDetectionScraper()
        await scraper.create_driver()
        
        # Mock captcha detection
        scraper.captcha_detector = Mock()
        scraper.captcha_detector.detect_captcha.return_value = True
        
        with pytest.raises(CaptchaDetectedError):
            await scraper.get_page_with_stealth("https://example.com")
            
    def test_quit(self):
        """Test driver cleanup"""
        scraper = AntiDetectionScraper()
        mock_driver = Mock()
        scraper.driver = mock_driver
        
        scraper.quit()
        
        mock_driver.quit.assert_called_once()
        assert scraper.driver is None
        
    def test_quit_with_exception(self):
        """Test driver cleanup with exception"""
        scraper = AntiDetectionScraper()
        mock_driver = Mock()
        mock_driver.quit.side_effect = Exception("Cleanup error")
        scraper.driver = mock_driver
        
        # Should not raise exception
        scraper.quit()
        assert scraper.driver is None


class TestSessionManager:
    """Test session management"""
    
    @pytest.fixture
    def temp_session_file(self, tmp_path):
        return str(tmp_path / "test_session.json")
        
    def test_init_no_file(self, temp_session_file):
        manager = SessionManager(temp_session_file)
        assert manager.session_data == {}
        
    def test_init_with_existing_file(self, temp_session_file):
        # Create a test session file
        import json
        test_data = {"test": "data"}
        with open(temp_session_file, 'w') as f:
            json.dump(test_data, f)
            
        manager = SessionManager(temp_session_file)
        assert manager.session_data == test_data
        
    def test_save_session(self, temp_session_file):
        manager = SessionManager(temp_session_file)
        manager.session_data = {"test": "save_data"}
        
        manager.save_session()
        
        # Verify file was created with correct content
        import json
        with open(temp_session_file, 'r') as f:
            saved_data = json.load(f)
        assert saved_data == {"test": "save_data"}
        
    def test_set_cookies(self, temp_session_file):
        manager = SessionManager(temp_session_file)
        manager.session_data = {
            "cookies": {
                "example.com": [
                    {"name": "test_cookie", "value": "test_value"}
                ]
            }
        }
        
        mock_driver = Mock()
        manager.set_cookies(mock_driver, "example.com")
        
        mock_driver.get.assert_called_once_with("https://example.com")
        mock_driver.add_cookie.assert_called_once_with({
            "name": "test_cookie", 
            "value": "test_value"
        })
        
    def test_save_cookies(self, temp_session_file):
        manager = SessionManager(temp_session_file)
        
        mock_driver = Mock()
        test_cookies = [{"name": "session", "value": "abc123"}]
        mock_driver.get_cookies.return_value = test_cookies
        
        manager.save_cookies(mock_driver, "example.com")
        
        assert manager.session_data["cookies"]["example.com"] == test_cookies


@patch('services.scraping_infrastructure.uc')
@patch('services.scraping_infrastructure.stealth')
@pytest.mark.asyncio
async def test_create_stealth_scraper(mock_stealth, mock_uc):
    """Test factory function"""
    from selenium.webdriver.chrome.webdriver import WebDriver
    mock_driver = Mock(spec=WebDriver)
    mock_driver.execute_script = Mock()
    mock_uc.Chrome.return_value = mock_driver
    
    scraper = await create_stealth_scraper(
        headless=False,
        proxy_list=["proxy1:8080"],
        request_delay=2.0
    )
    
    assert isinstance(scraper, AntiDetectionScraper)
    assert scraper.headless is False
    assert scraper.throttler.base_delay == 2.0
    assert scraper.driver is not None


if __name__ == "__main__":
    pytest.main([__file__])
