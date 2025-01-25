import requests
import json
from datetime import datetime

def test_api():
    print(f"\n=== Testing Reddit Analyzer API at {datetime.now()} ===\n")
    
    # Test endpoint
    username = "spez"  # Reddit co-founder's account as a test case
    url = f"http://localhost:5001/api/v1/analyze/{username}"
    
    try:
        print(f"Analyzing user: {username}")
        response = requests.get(url)
        
        # Check if request was successful
        if response.status_code == 200:
            data = response.json()
            print("\nResults:")
            print(f"Username: {data['username']}")
            print(f"Thinking Machine Probability: {data['probability']:.2f}%")
            print("\nSummary:")
            print(f"Account Age: {data['summary']['account_age']}")
            print(f"Karma: {data['summary']['karma']:,}")
        elif response.status_code == 429:
            print("Rate limit exceeded. Please wait before making another request.")
            retry_after = response.headers.get('Retry-After', 'unknown')
            print(f"Retry after: {retry_after} seconds")
        else:
            print(f"Error: Status code {response.status_code}")
            print(f"Message: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to the API. Make sure the server is running.")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    test_api()
