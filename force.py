import aiohttp
import asyncio
import json
import time
from urllib.parse import quote
from random import randint

from AminoLightPy.lib.util.helpers import signature, gen_deviceId

# Terminal color codes
PB = '\x1b[0;30;45m'
P = '\x1b[0;35;40m'
W = '\x1b[0;0m'
GB = '\x1b[0;30;42m'
G = '\x1b[0;32;40m'

# Initialize and login to Samino client
import samino

# Input email and password
email = input("Enter your email: ")
password = input("Enter your password: ")

c = samino.Client()
c.login(email=email, password=password)
comId = input("comId: ")  # Replace with your community ID
device = gen_deviceId()
device: str

# Asynchronous WebSocket connection
async def create_socket_connection(session: aiohttp.ClientSession, sid: str, device: str) -> aiohttp.ClientWebSocketResponse:
    try:
        milliseconds = int(time.time() * 1000)
        data = f"{device}|{milliseconds}"

        headers = {
            "NDCDEVICEID": device,
            "NDC-MSG-SIG": signature(data),
            "NDCAUTH": sid
        }

        wss_url = f"ws://ws{randint(1, 4)}.aminoapps.com:80/?signbody={quote(data)}"

        websocket = await session.ws_connect(
            url=wss_url,
            headers=headers,
            ssl=False,
        )

        return websocket
    except Exception as e:
        print(f"Error: {e}")
        return None

# Function to join a chat
async def join_chat(ws, chatId, userId=None):
    try:
        await ws.send_json({"o": {"ndcId": int(comId), "threadId": chatId, "id": int(time.time() * 1000)}, "t": 100})
        await ws.send_json({"o": {"ndcId": int(comId), "threadId": chatId, "joinRole": 1, "id": int(time.time() * 1000)}, "t": 112})
        await ws.send_json({"o": {"ndcId": int(comId), "threadId": chatId, "channelType": 4, "id": int(time.time() * 1000)}, "t": 108})
        await asyncio.sleep(1)
        if userId:
            await ws.send_json({'o': {'ndcId': int(comId), 'threadId': chatId, 'joinRole': 1, 'targetUid': userId, 'id': int(time.time() * 1000)}, 't': 126})

        print(f"{GB} ==❯ {G} Joined chat {chatId} {W} \n")
    except Exception as e:
        print(f"Error joining chat: {e}")

# Main function to handle video chat
async def run_video_chat():
    async with aiohttp.ClientSession() as session:
        # Get initial chat link and extract chatId
        link = input("Enter the chat link: ")
        chatId = c.get_from_link(link).objectId
        
        ws = await create_socket_connection(session, c.sid, device)
        if not ws:
            print("Failed to create WebSocket connection.")
            return

        while True:
            # Ask for user link or command
            user_link = input("Enter user link (or 'c' to change chat link): ")
            if user_link.lower() == 'c':
                # Change chat link
                link = input("Enter the new chat link: ")
                chatId = c.get_from_link(link).objectId
                print(f"{P}Chat link updated to {link}{W}")
                continue
            
            # Extract userId and join chat
            try:
                uid = c.get_from_link(user_link).objectId
                await join_chat(ws, chatId, userId=uid)
            except Exception as e:
                print(f"Error processing user link: {e}")

# Run the video chat process asynchronously
if __name__ == "__main__":
    asyncio.run(run_video_chat())
