
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
        # func: +1, for: +1, if: +1. Total: 3.
        self.assertEqual(analyze_complexity(code), 3)
        
    def test_complexity_script_toplevel(self):
        """
        Test that top-level script logic (no functions) is caught.
        """
        code = """
x = 0
for i in range(10): # +1
    if i % 2 == 0: # +1
        print(i)
    while x < 5: # +1
        x += 1
"""
        # Base 1 + 3 control flows = 4
        self.assertEqual(analyze_complexity(code), 4)

    @patch('ratemycode.analyzer.genai')
    def test_gemini_mock_json_extraction(self, mock_genai):
        mock_model = MagicMock()
        mock_response = MagicMock()
        # Simulate response with markdown blocks
        mock_response.text = 'Here is the JSON: ```json\n{"score": 85, "verdict": "Good code."}\n```'
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        
        score, verdict = analyze_with_gemini("fake_key", "print('hello')", "PROFESSIONAL")
        
        self.assertEqual(score, 85)
        self.assertEqual(verdict, "Good code.")

if __name__ == '__main__':
    unittest.main()
