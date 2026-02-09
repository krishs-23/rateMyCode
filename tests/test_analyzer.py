
import unittest
from unittest.mock import MagicMock, patch
from ratemycode.analyzer import analyze_complexity, analyze_with_gemini

class TestAnalyzer(unittest.TestCase):

    def test_complexity_simple(self):
        code = """
def simple():
    print("Hello")
"""
        # Complexity is 1 (base)
        self.assertEqual(analyze_complexity(code), 1)

    def test_complexity_nested(self):
        code = """
def nested():
    for i in range(10):
        if i % 2 == 0:
            print(i)
"""
        # Complexity is 3 (1 for func + 1 for loop + 1 for if) => wait, radon might be different.
        # Let's check radon logic. CC is usually 1 + branching points.
        # func: +1
        # for: +1
        # if: +1
        # Total: 3.
        self.assertEqual(analyze_complexity(code), 3)

    @patch('ratemycode.analyzer.genai')
    def test_gemini_mock(self, mock_genai):
        # Mocking the response
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '{"score": 85, "verdict": "Good code."}'
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        
        # Test
        score, verdict = analyze_with_gemini("fake_key", "print('hello')", "PROFESSIONAL")
        
        self.assertEqual(score, 85)
        self.assertEqual(verdict, "Good code.")

if __name__ == '__main__':
    unittest.main()
