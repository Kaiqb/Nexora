import asyncio
import pytest
from src.ai.nlu_service import NLUService

@pytest.mark.asyncio
async def test_nlu_extraction():
    nlu = NLUService()
    
    # Test basic business registration intent
    result = await nlu.extract_entities("I want to create an LLC called Tech Solutions in Texas")
    
    # Print detailed results
    print("\nExtracted Entities:")
    for key, value in result.items():
        if key != "raw_entities":  # Skip raw entities for cleaner output
            print(f"{key}: {value}")
    
    # Basic assertions
    assert result["business_type"] == "LLC"
    assert result["state_code"] == "TX"
    assert "Tech Solutions" in str(result["business_name"])

if __name__ == "__main__":
    asyncio.run(test_nlu_extraction())