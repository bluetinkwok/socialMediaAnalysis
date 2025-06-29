"""
Tests for the input sanitization module.
"""
import unittest
from core.input_sanitizer import InputSanitizer

class TestInputSanitizer(unittest.TestCase):
    """Test cases for InputSanitizer class."""
    
    def test_sanitize_string(self):
        """Test string sanitization for XSS prevention."""
        # Test with XSS payload
        xss_input = "<script>alert('XSS')</script>"
        sanitized = InputSanitizer.sanitize_string(xss_input)
        self.assertEqual(sanitized, "&lt;script&gt;alert(&#x27;XSS&#x27;)&lt;/script&gt;")
        
        # Test with None input
        self.assertEqual(InputSanitizer.sanitize_string(None), "")
        
        # Test with normal string
        self.assertEqual(InputSanitizer.sanitize_string("Hello World"), "Hello World")
        
    def test_sanitize_sql_input(self):
        """Test SQL injection sanitization."""
        # Test with SQL injection payload
        sql_input = "1; DROP TABLE users; --"
        sanitized = InputSanitizer.sanitize_sql_input(sql_input)
        self.assertNotIn(";", sanitized)
        self.assertNotIn("DROP TABLE", sanitized)
        
        # Test with None input
        self.assertEqual(InputSanitizer.sanitize_sql_input(None), "")
        
        # Test with normal string
        self.assertEqual(InputSanitizer.sanitize_sql_input("user123"), "user123")
        
    def test_sanitize_path(self):
        """Test path traversal sanitization."""
        # Test with path traversal payload
        path_input = "../../../etc/passwd"
        sanitized = InputSanitizer.sanitize_path(path_input)
        self.assertNotIn("..", sanitized)
        
        # Test with absolute path
        path_input = "/var/www/html/index.php"
        sanitized = InputSanitizer.sanitize_path(path_input)
        self.assertFalse(sanitized.startswith("/"))
        
        # Test with None input
        self.assertEqual(InputSanitizer.sanitize_path(None), "")
        
        # Test with normal path
        self.assertEqual(InputSanitizer.sanitize_path("images/avatar.png"), "images/avatar.png")
        
    def test_sanitize_command(self):
        """Test command injection sanitization."""
        # Test with command injection payload
        cmd_input = "file.txt; rm -rf /"
        sanitized = InputSanitizer.sanitize_command(cmd_input)
        self.assertNotIn(";", sanitized)
        self.assertNotIn("rm", sanitized)
        
        # Test with None input
        self.assertEqual(InputSanitizer.sanitize_command(None), "")
        
        # Test with normal command
        self.assertEqual(InputSanitizer.sanitize_command("echo hello"), "echo hello")
        
    def test_sanitize_url(self):
        """Test URL sanitization."""
        # Test with URL containing special characters
        url_input = "https://example.com/search?q=test&page=2"
        sanitized = InputSanitizer.sanitize_url(url_input)
        self.assertEqual(sanitized, "https://example.com/search?q=test&page=2")
        
        # Test with URL containing spaces and other characters
        url_input = "https://example.com/path with spaces?q=<test>"
        sanitized = InputSanitizer.sanitize_url(url_input)
        self.assertNotIn(" ", sanitized)
        self.assertNotIn("<", sanitized)
        self.assertNotIn(">", sanitized)
        
        # Test with None input
        self.assertEqual(InputSanitizer.sanitize_url(None), "")
        
    def test_sanitize_dict(self):
        """Test dictionary sanitization."""
        # Test with dictionary containing XSS payload
        dict_input = {
            "name": "<script>alert('XSS')</script>",
            "age": 25,
            "address": {
                "street": "<img src=x onerror=alert('XSS')>",
                "city": "New York"
            },
            "hobbies": ["reading", "<script>alert('XSS')</script>", "sports"]
        }
        
        sanitized = InputSanitizer.sanitize_dict(dict_input)
        
        # Check string values are sanitized
        self.assertEqual(sanitized["name"], "&lt;script&gt;alert(&#x27;XSS&#x27;)&lt;/script&gt;")
        
        # Check non-string values remain unchanged
        self.assertEqual(sanitized["age"], 25)
        
        # Check nested dictionary values are sanitized
        self.assertEqual(sanitized["address"]["street"], "&lt;img src=x onerror=alert(&#x27;XSS&#x27;)&gt;")
        self.assertEqual(sanitized["address"]["city"], "New York")
        
        # Check list values are sanitized
        self.assertEqual(sanitized["hobbies"][0], "reading")
        self.assertEqual(sanitized["hobbies"][1], "&lt;script&gt;alert(&#x27;XSS&#x27;)&lt;/script&gt;")
        self.assertEqual(sanitized["hobbies"][2], "sports")
        
    def test_sanitize_list(self):
        """Test list sanitization."""
        # Test with list containing XSS payload
        list_input = [
            "<script>alert('XSS')</script>",
            25,
            {"name": "<img src=x onerror=alert('XSS')>"},
            ["nested", "<script>alert('XSS')</script>"]
        ]
        
        sanitized = InputSanitizer.sanitize_list(list_input)
        
        # Check string values are sanitized
        self.assertEqual(sanitized[0], "&lt;script&gt;alert(&#x27;XSS&#x27;)&lt;/script&gt;")
        
        # Check non-string values remain unchanged
        self.assertEqual(sanitized[1], 25)
        
        # Check nested dictionary values are sanitized
        self.assertEqual(sanitized[2]["name"], "&lt;img src=x onerror=alert(&#x27;XSS&#x27;)&gt;")
        
        # Check nested list values are sanitized
        self.assertEqual(sanitized[3][0], "nested")
        self.assertEqual(sanitized[3][1], "&lt;script&gt;alert(&#x27;XSS&#x27;)&lt;/script&gt;")


if __name__ == "__main__":
    unittest.main() 