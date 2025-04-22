import asyncio
from spade.agent import Agent
from spade.behaviour import OneShotBehaviour
from spade.message import Message
from spade_mcp.mcp import MCPMixin, mcp_method


class ServerAgent(MCPMixin, Agent):

    @mcp_method(name="add", description="Adds two numbers")
    def add(self, a, b):
        return a + b

    @mcp_method(name="subtract", description="Subtracts two numbers")
    def subtract(self, a, b):
        return a - b

    async def setup(self):
        print(f"ServerAgent {self.jid} starting...")
        await super().setup()


class ClientAgent(Agent):
    class RequestBehaviour(OneShotBehaviour):
        async def run(self):
            # Create a message to send a request to the server
            msg = Message(to=self.agent.server_jid)
            msg.set_metadata("performative", "request")
            msg.body = '{"method": "add", "params": {"a": 5, "b": 3}, "id": 1}'

            # Send the message
            await self.send(msg)
            print("Request sent!")

            # Wait for the response
            response = await self.receive(timeout=10)
            if response:
                print(f"Response received: {response.body}")
            else:
                print("No response received.")

    def __init__(self, jid, password, server_jid):
        super().__init__(jid, password)
        self.server_jid = server_jid

    async def setup(self):
        print(f"ClientAgent {self.jid} starting...")
        self.add_behaviour(self.RequestBehaviour())


async def main():
    # Replace these with valid XMPP credentials
    server_jid = "server@localhost"
    server_password = "password"
    client_jid = "client@localhost"
    client_password = "password"

    # Create and start the server agent
    server_agent = ServerAgent(server_jid, server_password)
    await server_agent.start()

    # Create and start the client agent
    client_agent = ClientAgent(client_jid, client_password, server_jid)
    await client_agent.start()

    # Let the agents run for a while
    await asyncio.sleep(5)

    # Stop the agents
    await server_agent.stop()
    await client_agent.stop()


if __name__ == "__main__":
    asyncio.run(main())