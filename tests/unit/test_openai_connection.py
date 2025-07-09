import os
from openai import OpenAI

def test_openai_key(api_key: str):
    """
    Tests the provided OpenAI API key by making a simple API call.
    """
    if not api_key or not api_key.startswith("sk-"):
        print("\\n❌ Error: Invalid API key format. It should start with 'sk-'.")
        return

    print("\\nTesting your OpenAI API key...")
    try:
        # Initialize the client with the provided key
        client = OpenAI(api_key=api_key)
        
        # Make a simple, low-cost API call to list available models
        client.models.list()
        
        print("\\n✅ Success! Your OpenAI API key is working correctly.")
        
    except Exception as e:
        print(f"\\n❌ Error: The API key is not valid or there's a connection issue.")
        print("--------------------")
        print(f"Error Details: {e}")
        print("--------------------")
        print("\\nPlease check the following:")
        print("1. Is the API key copied correctly?")
        print("2. Is the key active on your OpenAI dashboard?")
        print("3. Does your OpenAI account have a valid payment method and sufficient funds?")

if __name__ == "__main__":
    # Prompt the user to enter their key securely
    user_api_key = input("Please paste your OpenAI API key and press Enter:\\n> ")
    test_openai_key(user_api_key) 