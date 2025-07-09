import os
import pytest
from openai import OpenAI

def test_openai_key():
    """
    Tests the OpenAI API key from environment variables.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        pytest.skip("OPENAI_API_KEY environment variable not set")
    
    if not api_key.startswith("sk-"):
        pytest.skip("API key doesn't start with 'sk-' - may be a different format or not valid")

    print("\nTesting your OpenAI API key...")
    try:
        # Initialize the client with the provided key
        client = OpenAI(api_key=api_key)
        
        # Make a simple, low-cost API call to list available models
        client.models.list()
        
        print("\n✅ Success! Your OpenAI API key is working correctly.")
        
    except Exception as e:
        pytest.fail(f"The API key is not valid or there's a connection issue: {e}")

if __name__ == "__main__":
    # Prompt the user to enter their key securely
    user_api_key = input("Please paste your OpenAI API key and press Enter:\n> ")
    
    # Test the provided key
    if not user_api_key or not user_api_key.startswith("sk-"):
        print("\n❌ Error: Invalid API key format. It should start with 'sk-'.")
    else:
        try:
            client = OpenAI(api_key=user_api_key)
            client.models.list()
            print("\n✅ Success! Your OpenAI API key is working correctly.")
        except Exception as e:
            print(f"\n❌ Error: The API key is not valid or there's a connection issue.")
            print("--------------------")
            print(f"Error Details: {e}")
            print("--------------------")
            print("\nPlease check the following:")
            print("1. Is the API key copied correctly?")
            print("2. Is the key active on your OpenAI dashboard?")
            print("3. Does your OpenAI account have a valid payment method and sufficient funds?") 