"""
scripts/08_smoke_test.py
========================
End-to-end smoke test for the OceanFlow API.
"""

import asyncio
import json
import sys
import time

import requests
import websockets

BASE_URL = "http://localhost:8000/api"
WS_URL = "ws://localhost:8000/api/ws"

def run_smoke_test():
    print("1. Submitting simulation...")
    body = {
        "region": {"west": -160, "east": -120, "south": 20, "north": 50},
        "time": {
            "start": "2024-01-01T00:00:00Z",
            "end": "2024-01-06T00:00:00Z",
            "timeStepHours": 6,
        },
        "particles": {
            "count": 500,
            "maxAgeDays": 30,
            "windagePercent": 1.5,
            "diffusionM2PerS": 50,
            "beachingEnabled": False,
        }
    }
    
    r = requests.post(f"{BASE_URL}/simulate", json=body)
    r.raise_for_status()
    run_id = r.json()["runId"]
    print(f"   -> Started run {run_id}")
    
    async def drain_ws():
        print(f"2. Connecting to WebSocket {WS_URL}/simulate/{run_id}")
        async with websockets.connect(f"{WS_URL}/simulate/{run_id}") as ws:
            async for message in ws:
                data = json.loads(message)
                if data["type"] == "progress":
                    print(f"   -> Progress: {data['percent']}%")
                elif data["type"] == "complete":
                    print("   -> Complete!")
                    break
                elif data["type"] == "snapshot":
                    print(f"   -> Snapshot status: {data['status']}")
                
    print("   Waiting for simulation to finish...")
    asyncio.run(drain_ws())
    
    print("3. Fetching meta and frame 0...")
    r = requests.get(f"{BASE_URL}/runs/{run_id}/meta")
    r.raise_for_status()
    meta = r.json()
    assert meta["particleCount"] == 500
    
    r = requests.get(f"{BASE_URL}/runs/{run_id}/frames/0")
    r.raise_for_status()
    assert int(r.headers["Content-Length"]) == 500 * 19
    print("   -> Frame 0 matches expected size (500 * 19 bytes)")
    
    print("4. Fetching density 0...")
    r = requests.get(f"{BASE_URL}/runs/{run_id}/density/0")
    r.raise_for_status()
    assert int(r.headers["Content-Length"]) == 720 * 360 * 4
    print("   -> Density 0 matches expected size (720 * 360 * 4 bytes)")
    
    print("5. Deleting run...")
    r = requests.delete(f"{BASE_URL}/runs/{run_id}")
    r.raise_for_status()
    print("   -> Run deleted")
    
    print("\nPASS")

if __name__ == "__main__":
    try:
        run_smoke_test()
    except Exception as e:
        print(f"\nFAIL: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
