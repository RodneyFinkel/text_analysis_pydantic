import os
import pytest
from unittest.mock import MagicMock
from langchain_core.messages import AIMessage, HumanMessage
from langchain_agent5 import AIAgent

@pytest.fixture
def isloated_agent(tmp_path):
    """Pytest fixture to craete a clean AIAgent in a temporary directory
        for every test, ensuring database artifacts dont cross-contaminate
    """
    agent = AIAgent(api_key="fake_groq_key_123", working_dir=str(tmp_path))
    return agent

class TestAIAgent:
    
    def test_agent_initialization(self, isolated_agent):
        """Check if the agent sets up the default SQLITE DB correctly"""
        assert os.path.exists(isolated_agent.db_path)
        assert len(isolated_agent.tools) == 7 # esnure all 7 tools are bound
        
    
    def test_list_available_databases(self, isolated_agent, tmp_path):
        """Test the local filesystem tool directly"""
        # Creat a dummy extra DB
        (tmp_path / "test_extra_db").touch()
        
        result = isolated_agent.list_available_databases()
        assert "student_grades,db" in result
        assert "test_extra_db" in result


