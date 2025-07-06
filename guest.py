#also does not work 
import os
import json
import aiohttp
import asyncio
import threading
from flask import Flask, render_template, jsonify
from time import time
from random import randint
from urllib.parse import quote
from AminoLightPy import Client
from AminoLightPy.lib.util.helpers import signature, gen_deviceId

if os.name == 'nt':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Global variables
socket_list = []
bandwidth_usage = 0  # Track bandwidth usage in bytes
app = Flask(__name__)

def get_ids_from_link(client: Client, link: str) -> tuple:
    """
    Extract IDs from the provided link using the Amino client.
    """
    link_data = client.get_from_code(code=link)
    comId = link_data.comId
    chatId = link_data.objectId
    return comId, chatId

async def create_socket_connection(session: aiohttp.ClientSession, device: str) -> aiohttp.ClientWebSocketResponse:
    """
    Create a WebSocket connection without the need for login or NDCAUTH.
    """
    while True:
        try:
            milliseconds = int(time() * 1000)
            data = f"{device}|{milliseconds}"

            headers = {
                "NDCDEVICEID": device,
                "NDC-MSG-SIG": signature(data)
            }

            wss_url = f"ws://ws{randint(1,4)}.aminoapps.com:80/?signbody={quote(data)}"

            websocket = await session.ws_connect(
                url=wss_url,
                headers=headers,
                ssl=False,
            )
            
            return websocket
        except Exception as e:
            print(f"WebSocket connection error: {e}. Reconnecting in 1 second...")
            await asyncio.sleep(1)

async def websocket_action(session: aiohttp.ClientSession, device: str, data: dict, repetitions: int) -> None:
    """
    Perform the WebSocket action multiple times and track bandwidth usage.
    """
    global bandwidth_usage
    data_s = json.dumps(data)

    for _ in range(repetitions):
        try:
            # Open a new WebSocket connection for each message
            websocket = await create_socket_connection(session, device)
            await websocket.send_str(data_s)
            print(f"WebSocket message sent: {data}")

            # Track bandwidth usage (size of the message sent)
            bandwidth_usage += len(data_s.encode('utf-8'))

            await websocket.close()  # Close the WebSocket after sending the message
        except Exception as e:
            print(f"Error while sending data: {e}")

def threaded_websocket_action(device: str, data: dict, repetitions: int, thread_count: int) -> None:
    """
    Run multiple threads for WebSocket actions.
    """
    async def run_in_thread():
        async with aiohttp.ClientSession() as session:
            print("\nStarting WebSocket actions...")
            await websocket_action(session, device, data, repetitions)

    # Start threads
    threads = []
    for _ in range(thread_count):
        thread = threading.Thread(target=asyncio.run, args=(run_in_thread(),))
        threads.append(thread)
        thread.start()

    # Wait for all threads to finish
    for thread in threads:
        thread.join()

@app.route('/')
def index():
    """
    Serve the HTML page for live bandwidth monitoring.
    """
    return render_template('index.html')

@app.route('/bandwidth', methods=['GET'])
def get_bandwidth():
    """
    Flask endpoint to get the current bandwidth usage in kilobytes.
    """
    global bandwidth_usage
    bandwidth_kb = bandwidth_usage / 1024  # Convert bytes to kilobytes
    response = jsonify({"bandwidth_usage_kb": bandwidth_kb})
    # Manually set CORS headers
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

def main():
    """
    Main function to set up WebSocket actions with dynamic thread ID.
    """
    print("WebSocket Automation Script")

    # Create the client
    client = Client(socket_enabled=False)


    # Input link to resolve
    link = input("Enter the link: ")
    try:
        comId, thread_id = get_ids_from_link(client, link)
    except Exception as e:
        print(f"Error resolving IDs from link: {e}")
        return

    if thread_id is None:
        print("Could not resolve thread ID from the provided link.")
        return

    # WebSocket Payload
    data = {
        "o": {
            "ndcId": comId,
            "threadId": thread_id,
            "joinRole": 2,
            "id": int(time() * 1000)
        },
        "t": 112
    }

    device = gen_deviceId()  # Device ID generation still needed for connection
    repetitions = 500  # Number of times to send the WebSocket message
    thread_count = int(input("Number of guest viewers: "))  # Number of threads to execute WebSocket actions concurrently

    try:
        # Start the threaded WebSocket action in a separate thread
        websocket_thread = threading.Thread(target=threaded_websocket_action, args=(device, data, repetitions, thread_count))
        websocket_thread.start()

        # Start the Flask server
        app.run(host="0.0.0.0", port=5000)
    except Exception as e:
        print(f"Error in main execution: {e}")

    print("WebSocket automation completed.")

if __name__ == "__main__":
    main()
