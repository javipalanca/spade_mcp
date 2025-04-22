"""Main module."""
import json
from spade.behaviour import CyclicBehaviour
from spade.message import Message
from spade.template import Template


def mcp_method(name=None, description=None):
    def decorator(func):
        func._mcp_method = True
        func._mcp_name = name or func.__name__
        func._mcp_description = description or ""
        return func
    return decorator


class MCPMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._mcp_methods = {}
        self._register_mcp_methods()

    def _register_mcp_methods(self):
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if callable(attr) and getattr(attr, "_mcp_method", False):
                method_name = attr._mcp_name
                self._mcp_methods[method_name] = {
                    "function": attr,
                    "description": attr._mcp_description
                }

    async def setup(self):
        mcp_behaviour = self.MCPBehaviour()
        template = Template()
        template.set_metadata("performative", "request")
        self.add_behaviour(mcp_behaviour, template)

    class MCPBehaviour(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=10)
            if msg:
                try:
                    request = json.loads(msg.body)
                    method_name = request.get("method")
                    params = request.get("params", {})
                    request_id = request.get("id")

                    if method_name == "rpc.introspect":
                        result = self._introspect()
                        response = {
                            "jsonrpc": "2.0",
                            "result": result,
                            "id": request_id
                        }
                    elif method_name in self.agent._mcp_methods:
                        method = self.agent._mcp_methods[method_name]["function"]
                        result = method(**params)
                        response = {
                            "jsonrpc": "2.0",
                            "result": result,
                            "id": request_id
                        }
                    else:
                        response = {
                            "jsonrpc": "2.0",
                            "error": {
                                "code": -32601,
                                "message": f"Método '{method_name}' no encontrado."
                            },
                            "id": request_id
                        }
                except json.JSONDecodeError:
                    response = {
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32700,
                            "message": "Error de parseo en el JSON."
                        },
                        "id": None
                    }
                except Exception as e:
                    response = {
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32603,
                            "message": f"Error interno: {str(e)}"
                        },
                        "id": request_id
                    }

                reply = Message(to=str(msg.sender))
                reply.set_metadata("performative", "inform")
                reply.body = json.dumps(response)
                await self.send(reply)

        def _introspect(self):
            return {
                name: {
                    "description": info["description"]
                } for name, info in self.agent._mcp_methods.items()
            }