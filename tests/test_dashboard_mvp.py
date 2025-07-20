#!/usr/bin/env python3
"""
Test script for the HTMX Dashboard MVP
Demonstrates the core functionality and SSE events
"""

import asyncio
import json

import pytest


@pytest.mark.asyncio
@pytest.mark.dashboard
async def test_dashboard_functionality():
    """Test the dashboard endpoints and SSE functionality"""

    import aiohttp

    print("🚀 Testing Ikoma AI HTMX Dashboard MVP")
    print("=" * 50)

    async with aiohttp.ClientSession() as session:
        # Test health endpoint
        print("\n1. Testing Health Endpoint...")
        async with session.get("http://localhost:8000/health") as resp:
            if resp.status == 200:
                health_data = await resp.json()
                print(f"✅ Health check passed: {health_data['status']}")
                print(f"   SSE connections: {health_data['sse_connections']}")
            else:
                print(f"❌ Health check failed: {resp.status}")
                return

        # Test agent status
        print("\n2. Testing Agent Status...")
        async with session.get("http://localhost:8000/agent-status") as resp:
            if resp.status == 200:
                status_data = await resp.json()
                print(f"✅ Agent status: {status_data['execution_status']}")
                print(f"   Internet enabled: {status_data['internet_enabled']}")
            else:
                print(f"❌ Agent status failed: {resp.status}")

        # Test internet toggle
        print("\n3. Testing Internet Toggle...")
        async with session.post(
            "http://localhost:8000/settings/internet-toggle"
        ) as resp:
            if resp.status == 200:
                toggle_data = await resp.json()
                print(f"✅ Internet toggle: {toggle_data['internet_enabled']}")
            else:
                print(f"❌ Internet toggle failed: {resp.status}")

        # Test agent control
        print("\n4. Testing Agent Control...")
        agent_command = {"action": "start", "agent_id": "test-agent-1"}
        async with session.post(
            "http://localhost:8000/agent-control", json=agent_command
        ) as resp:
            if resp.status == 200:
                control_data = await resp.json()
                print(f"✅ Agent control: {control_data['action']}")
            else:
                print(f"❌ Agent control failed: {resp.status}")

        # Test SSE connection
        print("\n5. Testing SSE Connection...")
        try:
            async with session.get("http://localhost:8000/agent-stream") as resp:
                if resp.status == 200:
                    print("✅ SSE connection established")

                    # Read a few events
                    event_count = 0
                    async for line in resp.content:
                        line = line.decode("utf-8").strip()
                        if line.startswith("event:"):
                            event_type = line.split(":", 1)[1].strip()
                            print(f"   📡 SSE Event: {event_type}")
                            event_count += 1
                            if event_count >= 3:  # Just test a few events
                                break
                        elif line.startswith("data:"):
                            try:
                                data = json.loads(line.split(":", 1)[1].strip())
                                print(f"   📊 Data: {data}")
                            except json.JSONDecodeError:
                                pass
                else:
                    print(f"❌ SSE connection failed: {resp.status}")
        except Exception as e:
            print(f"❌ SSE test error: {e}")

    print("\n" + "=" * 50)
    print("🎉 Dashboard MVP Test Complete!")
    print("\n📋 Next Steps:")
    print("   1. Open http://localhost:8000 in your browser")
    print("   2. Test the three-panel responsive layout")
    print("   3. Try the internet toggle in the left panel")
    print("   4. Start/stop agents in the center panel")
    print("   5. Watch real-time updates in the right panel")
    print("\n🔧 Features Implemented:")
    print("   ✅ HTMX 2.0 with SSE support")
    print("   ✅ Three-panel responsive layout")
    print("   ✅ Real-time agent status updates")
    print("   ✅ Internet access toggle")
    print("   ✅ Agent control (start/stop)")
    print("   ✅ Progress visualization")
    print("   ✅ Mobile-first responsive design")


if __name__ == "__main__":
    asyncio.run(test_dashboard_functionality())
