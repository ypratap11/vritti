import google.generativeai as genai
genai.configure(api_key="AIzaSyCxwqNDBjxFEvnJH1jVz61OAFgSr6L2KK4")
model = genai.GenerativeModel('gemini-1.5-flash')
response = model.generate_content("Hello, test")
print(response.text)