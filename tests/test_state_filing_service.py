import pytest
from src.ai.chat_service import ChatService
from src.ai.state_filing_service import StateFilingService

pytestmark = pytest.mark.asyncio

async def test_dynamic_state_detection():
    """Test that the system dynamically detects and handles different states"""
    chat = ChatService()
    
    test_cases = [
        "I want to register Tech Solutions LLC in Texas",
        "Register my business Sunshine Corp in California",
        "Start an LLC called Beach Rentals in Florida",
        "Create NewYork Ventures LLC in New York"  # Not yet supported
    ]
    
    for user_message in test_cases:
        print(f"\n{'='*70}")
        print(f"👤 User: {user_message}")
        print(f"{'='*70}")
        
        result = await chat.process_registration_request(user_message)
        
        print(f"\n🔍 Extracted State: {result['entities'].get('state_code')}")
        print(f"✅ Filing Available: {result['filing_available']}")
        
        if not result['filing_available']:
            print(f"⚠️  Supported states: {', '.join(result['supported_states'])}")
        
        print(f"🤖 Bot: {result['confirmation']}")
        print(f"➡️  Next: {result['suggested_next']}")

async def test_multi_state_filing():
    """Test filing with different states using same code"""
    chat = ChatService()
    
    # Mock entities for different states
    states_to_test = [
        {
            "state_code": "TX",
            "business_name": "Texas Tech LLC",
            "business_type": "LLC"
        },
        {
            "state_code": "CA",
            "business_name": "California Dreams LLC",
            "business_type": "LLC"
        },
        {
            "state_code": "FL",
            "business_name": "Florida Sunshine LLC",
            "business_type": "LLC"
        }
    ]
    
    for entities in states_to_test:
        print(f"\n{'='*70}")
        print(f"Testing {entities['state_code']} - {entities['business_name']}")
        print(f"{'='*70}")
        
        if StateFilingService.is_state_supported(entities['state_code']):
            print(f"✅ {entities['state_code']} is supported")
            # Uncomment to test actual filing:
            # result = await chat.file_with_state(entities, "username", "password")
            # print(result)
        else:
            print(f"⚠️  {entities['state_code']} not yet configured")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_dynamic_state_detection())