# gemini_test.py - Test your Gemini API key
"""
Simple test script for Gemini API on Windows
Run this to verify your API key works before integrating with your app
"""

import os
import requests
import json
from typing import Optional


def test_gemini_api(api_key: str) -> bool:
    """Test Gemini API with a simple request"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"

    headers = {
        "Content-Type": "application/json"
    }

    data = {
        "contents": [
            {
                "parts": [
                    {
                        "text": "Hello! Can you help me process invoices? Just say yes or no."
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.7,
            "topK": 40,
            "topP": 0.95,
            "maxOutputTokens": 100
        }
    }

    try:
        print("🔄 Testing Gemini API...")
        response = requests.post(url, headers=headers, json=data, timeout=30)

        if response.status_code == 200:
            result = response.json()

            if 'candidates' in result and len(result['candidates']) > 0:
                text_response = result['candidates'][0]['content']['parts'][0]['text']
                print("✅ SUCCESS! Gemini API is working!")
                print(f"📝 Response: {text_response}")
                return True
            else:
                print("❌ ERROR: No response content received")
                print(f"📄 Full response: {json.dumps(result, indent=2)}")
                return False

        else:
            print(f"❌ ERROR: HTTP {response.status_code}")
            print(f"📄 Response: {response.text}")
            return False

    except requests.exceptions.Timeout:
        print("❌ ERROR: Request timed out (30 seconds)")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ ERROR: Request failed - {e}")
        return False
    except Exception as e:
        print(f"❌ ERROR: Unexpected error - {e}")
        return False


def test_with_invoice_context(api_key: str) -> bool:
    """Test with invoice-specific context"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"

    headers = {"Content-Type": "application/json"}

    data = {
        "contents": [
            {
                "parts": [
                    {
                        "text": """You are an AI assistant for invoice processing. 
                        A user asks: "Show me my pending invoices"

                        How would you respond? Keep it brief."""
                    }
                ]
            }
        ]
    }

    try:
        print("\n🔄 Testing with invoice context...")
        response = requests.post(url, headers=headers, json=data, timeout=30)

        if response.status_code == 200:
            result = response.json()
            text_response = result['candidates'][0]['content']['parts'][0]['text']
            print("✅ Invoice context test successful!")
            print(f"📝 AI Response: {text_response}")
            return True
        else:
            print(f"❌ Invoice context test failed: HTTP {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Invoice context test error: {e}")
        return False


def test_gemini_with_google_ai_library(api_key: str) -> bool:
    """Test using Google's official library (if installed)"""

    try:
        import google.generativeai as genai

        print("\n🔄 Testing with Google AI library...")

        # Configure the API key
        genai.configure(api_key=api_key)

        # Create model
        model = genai.GenerativeModel('gemini-1.5-flash')

        # Generate content
        response = model.generate_content("Hello! Test message for invoice AI system.")

        print("✅ Google AI library test successful!")
        print(f"📝 Response: {response.text}")
        return True

    except ImportError:
        print("\n⚠️ Google AI library not installed")
        print("💡 To install: pip install google-generativeai")
        return False
    except Exception as e:
        print(f"❌ Google AI library test failed: {e}")
        return False


def main():
    """Main test function"""

    print("🧪 GEMINI API TEST SUITE")
    print("=" * 50)

    # Get API key from environment or input
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        print("🔑 API key not found in environment variables")
        api_key = input("Please enter your Gemini API key: ").strip()

    if not api_key:
        print("❌ No API key provided. Exiting.")
        return

    # Mask API key for display
    masked_key = f"{api_key[:8]}...{api_key[-8:]}" if len(api_key) > 16 else "***"
    print(f"🔑 Using API key: {masked_key}")
    print()

    # Run tests
    tests_passed = 0
    total_tests = 0

    # Test 1: Basic API test
    total_tests += 1
    if test_gemini_api(api_key):
        tests_passed += 1

    # Test 2: Invoice context test
    total_tests += 1
    if test_with_invoice_context(api_key):
        tests_passed += 1

    # Test 3: Google AI library test
    total_tests += 1
    if test_gemini_with_google_ai_library(api_key):
        tests_passed += 1

    # Results
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS")
    print(f"✅ Tests passed: {tests_passed}/{total_tests}")

    if tests_passed == total_tests:
        print("🎉 ALL TESTS PASSED! Your Gemini API is ready!")
        print("\n💡 Next steps:")
        print("1. Add GEMINI_API_KEY to your .env file")
        print("2. Test your conversation endpoint")
        print("3. Try the /conversation/test endpoint")
    elif tests_passed > 0:
        print("⚠️ Some tests passed. Check the errors above.")
    else:
        print("❌ All tests failed. Please check your API key.")

    print("\n🔗 Useful links:")
    print("- Google AI Studio: https://aistudio.google.com/")
    print("- Gemini API docs: https://ai.google.dev/docs")


if __name__ == "__main__":
    main()