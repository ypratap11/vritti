# gemini_troubleshoot.py - Debug Gemini API issues
import requests
import json


def check_api_key_format(api_key):
    """Check if API key has the right format"""
    print(f"🔍 API Key Analysis:")
    print(f"   Length: {len(api_key)} characters")
    print(f"   Starts with: {api_key[:10]}...")
    print(f"   Format looks correct: {'✅' if api_key.startswith('AIza') and len(api_key) == 39 else '❌'}")
    return api_key.startswith('AIza') and len(api_key) == 39


def test_different_endpoints(api_key):
    """Try different Gemini endpoints"""

    endpoints = [
        ("Gemini Pro",
         f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}"),
        ("Gemini Flash",
         f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"),
        ("List Models", f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}")
    ]

    for name, url in endpoints:
        print(f"\n🔄 Testing {name}...")

        try:
            if "models?" in url:
                # List models endpoint
                response = requests.get(url, timeout=10)
            else:
                # Generate content endpoint
                data = {
                    "contents": [{"parts": [{"text": "Hello"}]}]
                }
                response = requests.post(url, json=data, timeout=10)

            print(f"   Status: {response.status_code}")

            if response.status_code == 200:
                print(f"   ✅ {name} works!")
                if "models?" in url:
                    models = response.json().get('models', [])
                    print(f"   Available models: {len(models)}")
                return True
            else:
                error_info = response.json() if response.headers.get('content-type', '').startswith(
                    'application/json') else response.text
                print(f"   ❌ Error: {error_info}")

        except Exception as e:
            print(f"   ❌ Exception: {e}")

    return False


def get_new_api_key_instructions():
    """Print instructions for getting a new API key"""
    print("""
🔑 HOW TO GET A NEW GEMINI API KEY:

1. Go to Google AI Studio: https://aistudio.google.com/
2. Sign in with your Google account
3. Click "Get API key" in the top navigation
4. Click "Create API key in new project" 
5. Copy the new key (starts with AIza...)

⚠️ IMPORTANT SETTINGS:
- Remove all API restrictions (or set to "None")
- Make sure you're in the same Google account
- Wait 5-10 minutes after creating the key

🔧 ALTERNATIVE - Use Google Cloud Console:
1. Go to: https://console.cloud.google.com/
2. Enable "Generative Language API"
3. Go to Credentials > Create Credentials > API Key
4. Set restrictions to "None" for testing
""")


def main():
    print("🧪 GEMINI API TROUBLESHOOTER")
    print("=" * 40)

    # Get API key
    api_key = input("Enter your Gemini API key: ").strip()

    if not api_key:
        print("❌ No API key provided")
        return

    # Check format
    if not check_api_key_format(api_key):
        print("\n❌ API key format looks wrong!")
        print("   Gemini keys should start with 'AIza' and be 39 characters long")
        get_new_api_key_instructions()
        return

    # Test endpoints
    if test_different_endpoints(api_key):
        print("\n🎉 SUCCESS! At least one endpoint works!")
        print("💡 Try updating your .env file with this key")
    else:
        print("\n❌ All endpoints failed")
        print("🔧 NEXT STEPS:")
        print("1. Generate a new API key")
        print("2. Remove all restrictions")
        print("3. Wait 10 minutes and try again")
        print("4. Check if Generative Language API is enabled")
        get_new_api_key_instructions()


if __name__ == "__main__":
    main()