import base64
import itertools
import os
import re
import time
import json
import pandas as pd
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import NoSuchElementException
from constant import *
from webdriver_manager.chrome import ChromeDriverManager

from bs4 import BeautifulSoup

# Set up the webdriver
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

pattern = r"Episode (\d+(\.\d+)?|Spesial)"

def scrapeAnime(url, name):
    driver.get(url)
    time.sleep(5)

    soup = BeautifulSoup(driver.page_source, 'html.parser')

    tableT = soup.find("table", {"class":"episode_list"})

    result = []

    if(tableT):
        tbodyT = tableT.find("tbody")
        trT = tbodyT.find_all("tr", {"class":"episode-list-data"})
        for t in trT:
            tdEpisodeT = t.find("td", {"class":"episode-number"}).text.strip()
            tdTitleT = t.find("td", {"class":"episode-title"}).find("a").text.strip()

            result.append({
                "episode": tdEpisodeT,
                "title": tdTitleT
            })

    file_path = "AnimeList"+name+".json"

    # # Writing list to JSON file
    with open(file_path, "w") as json_file:
        json.dump(result, json_file)

    print("Profile data saved to data.json")


    driver.quit()

# Function to scrape a LinkedIn profile
def scrape(profile_url):
    result = []
    driver.get(profile_url)
    time.sleep(5)

    soup = BeautifulSoup(driver.page_source, 'html.parser')

    divTitle = soup.find('div', class_='item meta')

    title = ""
    if(divTitle):
        subDivTitle = divTitle.find("div", class_='lm')
        if(subDivTitle):
            title = subDivTitle.find("h1").text.strip()
    
    if(title != ""):
        match = re.search(pattern, title)
        title = match.group(1)

    dropdown = soup.find('select', {'class': 'mirror'})  # Replace 'dropdown-id' with the actual id

    options = dropdown.find_all('option')

    # Extract and print all option values
    for option in options:
        value = option.get('value')
        text = option.text.strip()

        if(value):
            decoded_bytes = base64.b64decode(value)
            decoded_string = decoded_bytes.decode('utf-8')
            result.append({
                "episode":title,
                "type": text,
                "iframe": decoded_string
            })

    return result


    
    # name_div = soup.find('div', {'class': 'player-embed'})
    # iframe_tag = ""
    # if(name_div):
    #     iframe_tag = name_div.find("iframe")
    

    # return iframe_tag


def get_all_link(url, name):
    result = []
    driver.get(url)
    time.sleep(5)

    soup = BeautifulSoup(driver.page_source, 'html.parser')

    ul = soup.find("ul", {"id":"daftarepisode"})

    if(ul):
        li = ul.find_all("li")
        for l in li:
            span = l.find("span", class_="lchx")
            href = span.find("a").get("href")
            result.append(href)

    file_path = "link"+name+".json"

    # Writing list to JSON file
    with open(file_path, "w") as json_file:
        json.dump(result, json_file)

def get_arc_by_episode(number):
    num = 0
    if '-' in number:
        parts = number.split('-')
        # Convert the first part to an integer
        num = int(parts[0])
    else:
        num = int(number)
    for arc, episode_range in arcs.items():
        if num in episode_range:
            return arc
    return "Unknown Arc"



# Function to check which arc an episode belongs to based on the index
def get_arc_by_index(index):
    episode_num = index + 1  # Convert 0-based index to 1-based episode number
    for arc, episode_range in arcs.items():
        if episode_num in episode_range:
            return arc
    return "Unknown Arc"


def check_480p_only(group):
    # Iterate through each item in the group
    for item in group:
        if "480p" not in item["type"]:
            return False  # Return False if any type is not 480p
    return True  # Return True if all types are 480p


def insertDataToNevv(fileName, reverse):
    # API endpoint URL
    url = 'https://www.nevv.io/api/theater/pc/add'
    data = []
    with open(fileName, 'r') as file:
        data = json.load(file)

    if(reverse == True):
        data = data[::-1]

    for d in data:

        # Sending POST request
        response = requests.post(url, json=d)

        # Checking the response
        if response.status_code == 200:
            print("Success")  # Print the response data
        else:
            print("Failed")  # Print error details

# Main script
if __name__ == "__main__":

    #1: dapatkan link episode
    # get_all_link("https://v9.animasu.cc/anime/solo-leveling-s2/", "SoloLevelingSeason2")

    #2: dapatkan semua iframenya nya
    # data = []
    # result = []
    # with open("linkSoloLevelingSeason2.json", 'r') as file:
    #     data = json.load(file)
    # for da in data:
    #     result.append(scrape(da))
    # with open("SoloLevelingSeason2Iframe.json", "w") as json_file:
    #     json.dump(result, json_file)


    #3: filter iframenya
    data = []
    with open('SoloLevelingSeason2Iframe.json', 'r') as file:
        data = json.load(file)

    excluded_keywords = ["berkasdrive","mega","blogger",  "terabox",  "short.ink"]


    priority = ["blogger", "short.ink", "berkasdrive","mega","terabox"]

    result = []

    for episode_group in data:
        valid_entries = [entry for entry in episode_group if "480p" not in entry["type"]]
        
        if valid_entries:
            best_entry = min(valid_entries, key=lambda x: next((i for i, domain in enumerate(priority) if domain in x["iframe"]), float('inf')))
            result.append(best_entry)

    file_path = "SoloLevelingSeason2IframeFinal.json"
    with open(file_path, "w") as json_file:
        json.dump(result, json_file)

    print("Profile data saved to data.json")

    # 4: set the data HARUS DAPAT LIST TITLENYA DULU
    # data = []
    # title = []
    # result = []
    # with open('SoloLevelingSeason2IframeFinal.json', 'r') as file:
    #     data = json.load(file)

    # data = data[::-1]

    # with open('SoloLevelingSeason2Title.json', 'r') as file:
    #     title = json.load(file)


    # for idx, url in enumerate(data):
    #     result.append({
    #         "title": "SOLO LEVELING SEASON 2 EPISODE "+str(idx + 1)+" - "+title[idx]["title"].upper(),
    #         "url":url["iframe"],
    #         "beginTime": 1738624200000,
    #         "endTime": 1738624200000,
    #         "filterTheaterId": 55,
    #         "description": title[idx]["title"],
    #         "gameTypeId": "7361283002bf4a06b5e908516dec1f55",
    #         "hostId": "41602b8106804a898ee2976a29c3d114",
    #         "images": title[idx]["img"],
    #         "type":"CONTENT",
    #         "isPortrait":0
    #     })

    # file_path = "SoloLevelingSeason2.json"

    # # # Writing list to JSON file
    # with open(file_path, "w") as json_file:
    #     json.dump(result, json_file)


    # 5: input ke nevv
    # insertDataToNevv("SoloLevelingSeason2.json", False)
    
# cara run program scrapping
# source venv/bin/activate  
# python scrappingAnime.py  
