#!/usr/bin/env python

"""Tests for `spade_mcp` package."""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock
from spade_mcp.mcp import MCPMixin, mcp_method


class TestMCPMixin:
    @pytest.fixture
    def mock_agent(self):
        class MockAgent(MCPMixin):
            def __init__(self):
                super().__init__()
                self.add_behaviour = MagicMock()

            @mcp_method(name="test_method", description="A test method")
            def test_method(self, param1, param2):
                return param1 + param2

        return MockAgent()

    def test_register_mcp_methods(self, mock_agent):
        assert "test_method" in mock_agent._mcp_methods
        assert mock_agent._mcp_methods["test_method"]["description"] == "A test method"

    
    async def test_setup_mcp(self, mock_agent):
        await mock_agent._setup_mcp()
        assert mock_agent.add_behaviour.called
        behaviour, template = mock_agent.add_behaviour.call_args[0]
        assert isinstance(behaviour, MCPMixin.MCPBehaviour)
        assert template.get_metadata("performative") == "request"

    
    async def test_mcp_behaviour_introspect(self, mock_agent):
        behaviour = MCPMixin.MCPBehaviour()
        behaviour.agent = mock_agent
        behaviour.receive = AsyncMock(return_value=MagicMock(
            body='{"method": "rpc.introspect", "id": 1}',
            sender="test_sender@server"
        ))
        behaviour.send = AsyncMock()

        await behaviour.run()

        behaviour.send.assert_called_once()
        response = json.loads(behaviour.send.call_args[0][0].body)
        assert response["result"] == {"test_method": {"description": "A test method"}}
        assert response["id"] == 1

    @pytest.mark.asyncio
    async def test_mcp_behaviour_valid_method(self, mock_agent):
        behaviour = MCPMixin.MCPBehaviour()
        behaviour.agent = mock_agent
        behaviour.receive = AsyncMock(return_value=MagicMock(
            body='{"method": "test_method", "params": {"param1": 2, "param2": 3}, "id": 2}',
            sender="test_sender@server"
        ))
        behaviour.send = AsyncMock()

        await behaviour.run()

        behaviour.send.assert_called_once()
        response = json.loads(behaviour.send.call_args[0][0].body)
        assert response["result"] == 5
        assert response["id"] == 2

    
    async def test_mcp_behaviour_invalid_method(self, mock_agent):
        behaviour = MCPMixin.MCPBehaviour()
        behaviour.agent = mock_agent
        behaviour.receive = AsyncMock(return_value=MagicMock(
            body='{"method": "non_existent_method", "id": 3}',
            sender="test_sender@server"
        ))
        behaviour.send = AsyncMock()

        await behaviour.run()

        behaviour.send.assert_called_once()
        response = json.loads(behaviour.send.call_args[0][0].body)
        assert response["error"]["code"] == -32601
        assert response["error"]["message"] == "Método 'non_existent_method' no encontrado."
        assert response["id"] == 3


    async def test_mcp_behaviour_json_parse_error(self, mock_agent):
        behaviour = MCPMixin.MCPBehaviour()
        behaviour.agent = mock_agent
        behaviour.receive = AsyncMock(return_value=MagicMock(
            body='invalid_json',
            sender="test_sender@server"
        ))
        behaviour.send = AsyncMock()

        await behaviour.run()

        behaviour.send.assert_called_once()
        response = json.loads(behaviour.send.call_args[0][0].body)
        assert response["error"]["code"] == -32700
        assert response["error"]["message"] == "Error de parseo en el JSON."
        assert response["id"] is None
