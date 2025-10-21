import pytest
from src.ai.chat_service import ChatService

pytestmark = pytest.mark.asyncio

async def test_chat_service_full_flow():
    """Test ChatService using BOTH LLM (human responses) + NLU (entity extraction)"""
    chat = ChatService()
    
    test_prompt = "I want to register an LLC called Tech Solutions in Texas"
    print(f"\n{'='*70}")
    print(f"👤 User Input: '{test_prompt}'")
    print(f"{'='*70}")
    
    result = await chat.process_registration_request(test_prompt)
    
    print("\n🔍 NLU EXTRACTED ENTITIES (Structured Data):")
    print("-" * 70)
    for key, value in result['entities'].items():
        if key != "raw_entities" and value is not None:
            print(f"  ✓ {key:20s}: {value}")
    
    print("\n🤖 LLM GENERATED RESPONSE (Human-like):")
    print("-" * 70)
    print(f"  Bot: {result['confirmation']}")
    
    print("\n➡️  WORKFLOW ENGINE NEXT STEP:")
    print("-" * 70)
    print(f"  Action: {result['suggested_next']}")
    
    print(f"\n{'='*70}\n")
    
    # Verify both NLU and LLM worked
    assert result["entities"]["business_type"] == "LLC", "NLU failed to extract business type"
    assert result["entities"]["state_code"] == "TX", "NLU failed to extract state"
    assert len(result["confirmation"]) > 10, "LLM failed to generate response"
    assert result["suggested_next"] == "proceed_to_registration_form"
    
    print("✅ Success! Both NLU (entity extraction) and LLM (conversation) working together!")