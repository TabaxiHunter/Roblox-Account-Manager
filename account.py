import urllib.parse
import os

from playwright.sync_api import sync_playwright
from time import time
from random import randint

def get_security(cookies):
    for cookie in cookies:
        if cookie["name"] == ".ROBLOSECURITY":
            return cookie["value"]

class Account:
    def __init__(self, user_id, user_name, token):
        self.user_id = user_id
        self.user_name = user_name
        self.token = token

    def __get_csrf(self, context):
        response = context.request.post("https://auth.roblox.com/v1/authentication-ticket/")
        data = response.headers
        
        return data["x-csrf-token"]

    def __get_auth(self, context, client, csrf):
        response = context.request.post("https://auth.roblox.com/v1/authentication-ticket/", data={
            "clientAssertion": client
        },
        headers={
            "Referer": "https://www.roblox.com/",
            "Origin": "https://roblox.com",
            "X-CSRF-TOKEN": csrf
        })
            
        return response.headers["rbx-authentication-ticket"]

    def __get_client(self, context):
        response = context.request.get("https://auth.roblox.com/v1/client-assertion/")
        data = response.json()
        
        return data["clientAssertion"]

    def __get_job(self, context, server_id, place_id):
        response = context.request.post("https://gamejoin.roblox.com/v1/join-game-instance", data={
            "placeId": place_id,
            "isTeleport": False,
            "gameId": server_id,
            "gameJoinAttemptId": server_id
        },
        headers={
            "Referer": f"https://www.roblox.com/games/{place_id}/",
            "Origin": "https://roblox.com",
            "User-Agent": "Roblox/WinInet"
        })
        
        return response.json()["jobId"]

    def __get_server(self, context, place_id):
        response = context.request.get(f"https://games.roblox.com/v1/games/{place_id}/servers/Public")
        data = response.json()
        
        try:
            server_id = data["data"][0]["id"]
            return server_id
        
        except KeyError:
            return None

    def join_game(self, place_id):
        with sync_playwright() as playwright:
            chromium = playwright.webkit
            browser = chromium.launch()

            context = browser.new_context(bypass_csp=True)
            context.add_cookies([{
                "name": ".ROBLOSECURITY", "value": self.token, "domain": ".roblox.com", "path": "/"}
            ])
            
            server_id = self.__get_server(context, place_id)

            if server_id is None:
                return # TODO: Let user know the place id is invalid

            job = self.__get_job(context, server_id, place_id)
            client = self.__get_client(context)
            csrf = self.__get_csrf(context)
            ticket = self.__get_auth(context, client, csrf)

            launch_time = int(time())
            browser_tracker = str(randint(100000, 175000)) + str(randint(100000, 900000)) # I blame ic3 for this abomination

            url = f"https://assetgame.roblox.com/game/PlaceLauncher.ashx?request=RequestGame{job}&browserTrackerId={browser_tracker}&placeId={place_id}&gameId={job}&isPlayTogetherGame=false&isTeleport=false"
            url = urllib.parse.quote_plus(url)
            args = f"roblox-player:1+launchmode:play+gameinfo:{ticket}+launchtime:{launch_time}+placelauncherurl:{url}+browsertrackerid:{browser_tracker}+robloxLocale:en_us+gameLocale:en_us+channel:+LaunchExp:InApp"

            # Find the latest version of the Roblox client on the user's computer
            # I haven't tested this yet so hopefully works on all devices
            roblox_path = os.path.join(os.getenv("LOCALAPPDATA"), "Roblox\Versions")
            client_path = None

            for root, _, files in os.walk(roblox_path):
                for file in files:
                    if file == "RobloxPlayerBeta.exe":
                        client_path = os.path.join(root, file)

            if client_path:
                os.system(client_path + " " + args)