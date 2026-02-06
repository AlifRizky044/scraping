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


def insertYoutubeVideos(url):
    result = {}

    driver.get(url)
    time.sleep(5)
    video_id = ""
    match = re.search(r"youtu\.be/([^?]+)", url)
    if match:
        video_id = match.group(1)
        print(video_id)

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    title = soup.find("div", {"id":"above-the-fold"})
    title2 = title.find("div", {"id":"title"})
    title3 = title2.find("h1")
    title4 = title3.find("yt-formatted-string")
    if title4:
        print(title4.text)
        cleanTitle = title4.text.upper()
        result = {
            "title": title4.text.upper(),
            "url":setIframe3(video_id,cleanTitle),
            "beginTime": 1712832456123,
            "endTime": 1712832456123,
            "filterTheaterId":57,
            "description": cleanTitle,
            "gameTypeId": "ce40102ff458454980b4b40d9b1b476d",
            "hostId": "f25940ae8b774acb983dbc20237fbd4a",
            "images": "https://img.youtube.com/vi/"+video_id+"/maxresdefault.jpg",
            "type":"CONTENT",
            "isPortrait":0
        }

    return result

    # file_path = "Pokemon2.json"

    # # Writing list to JSON file
    # with open(file_path, "w") as json_file:
    #     json.dump(result, json_file)

    # titleSub = title.find("h1", {"class":"ytd-watch-metadata"})
    # print(title4)
    




def cleanShorts():
    data = []
    result = []
    with open("m6-shorts.json", 'r') as file:
        data = json.load(file)


    for d in data:
        for game in d["games"]:
            # Remove hashtags
            cleanTitle = d["match"]+" "+game["game"]+" - M6 WORLD CHAMPIONSHIP"

            match = re.search(r"shorts/([a-zA-Z0-9_-]+)", game["link"])
            if match:
                video_id = match.group(1)

                result.append({
                    "title": cleanTitle.upper(),
                    "url":setIframe2(game["link"],cleanTitle, "/shorts/"),
                    "beginTime": 1729098000000,
                    "endTime": 1729184400000,
                    "filterTheaterId":53,
                    "description": cleanTitle,
                    "gameTypeId": "a56d1c3b08df436dbb774401f9a81a43",
                    "hostId": "41602b8106804a898ee2976a29c3d114",
                    "images": "https://img.youtube.com/vi/"+video_id+"/maxresdefault.jpg",
                    "type":"CONTENT",
                    "isPortrait":1
                })
    file_path = "M6-shorts-nevv.json"

    # Writing list to JSON file
    with open(file_path, "w") as json_file:
        json.dump(result, json_file)

    


def scrapeAnime(url):
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

    file_path = "AnimeListOnePiece.json"

    # # Writing list to JSON file
    with open(file_path, "w") as json_file:
        json.dump(result, json_file)

    print("Profile data saved to data.json")


    driver.quit()

def setIframe(url, title, elementToReplace):
    iframe = '''<iframe width="560" height="315" src="https://www.youtube.com/embed/imHt_slq_3c?autoplay=1" title="VALORANT Game Changers Championship - Lower Round 2 - Day 4" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>'''

    embed_url = url.replace(elementToReplace, "/embed/")
    embed_url = url.replace("?feature=share", "")
    updated_iframe = re.sub(r'src="[^"]+"', f'src="https://www.youtube.com{embed_url}?autoplay=1"', iframe)
    updated_iframe = re.sub(r'title="[^"]+"', f'title="{title}"', updated_iframe)

    return updated_iframe

def setIframe2(url, title, elementToReplace):
    iframe = '''<iframe width="560" height="315" src="https://www.youtube.com/embed/imHt_slq_3c?autoplay=1" title="VALORANT Game Changers Championship - Lower Round 2 - Day 4" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>'''

    embed_url = url.replace(elementToReplace, "/embed/")
    embed_url = re.sub(r'\?si=.*', '', embed_url)
    embed_url = embed_url.replace("?feature=share", "")
    updated_iframe = re.sub(r'src="[^"]+"', f'src="{embed_url}?autoplay=1"', iframe)
    updated_iframe = re.sub(r'title="[^"]+"', f'title="{title}"', updated_iframe)

    return updated_iframe

def setIframe3(video_id, title):
    iframe = '''<iframe width="560" height="315" src="https://www.youtube.com/embed/imHt_slq_3c?autoplay=1" title="VALORANT Game Changers Championship - Lower Round 2 - Day 4" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>'''

    embed_url = "https://www.youtube.com/embed/"+video_id
    updated_iframe = re.sub(r'src="[^"]+"', f'src="{embed_url}?autoplay=1"', iframe)
    updated_iframe = re.sub(r'title="[^"]+"', f'title="{title}"', updated_iframe)

    return updated_iframe


def scrapeYoutubeVideos(url):
    driver.get(url)
    result = []
    time.sleep(20)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    aYou = soup.find_all('a', {"id":'video-title-link'})
    for option in aYou:
        value = option.get('href')
        title = option.get('title')
        # Remove hashtags
        cleanTitle = re.sub(r"#\S+", "", title).strip()

        # Remove emojis and non-ASCII characters (but keep all symbols like @, &, etc.)
        cleanTitle = re.sub(r'[^\x00-\x7F]+', '', cleanTitle)

        result.append({
            "title": cleanTitle,
            "url":setIframe(value,cleanTitle, "/watch?v="),
            "beginTime": 1729098000000,
            "endTime": 1729184400000,
            "filterTheaterId":52,
            "description": cleanTitle,
            "gameTypeId": "25dcdf00f13d41c18b934a58afdb1e16",
            "hostId": "41602b8106804a898ee2976a29c3d114",
            "images": "https://img.youtube.com/vi/"+value.replace("/watch?v=", "")+"/maxresdefault.jpg",
            "type":"CONTENT",
            "isPortrait":0
        })
    file_path = "Pokemon.json"

    # Writing list to JSON file
    with open(file_path, "w") as json_file:
        json.dump(result, json_file)

    driver.quit()


def scrapeYoutubeShorts(url):
    driver.get(url)
    result = []
    time.sleep(20)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    aYou = soup.find_all('a', class_='ShortsLockupViewModelHostOutsideMetadataEndpoint')
    for option in aYou:
        value = option.get('href')
        title = option.get('title')
        # Remove hashtags
        cleanTitle = re.sub(r"#\S+", "", title).strip()

        # Remove emojis and non-ASCII characters (but keep all symbols like @, &, etc.)
        cleanTitle = re.sub(r'[^\x00-\x7F]+', '', cleanTitle)

        result.append({
            "title": cleanTitle,
            "url":setIframe(value,cleanTitle, "/shorts/"),
            "beginTime": 1729098000000,
            "endTime": 1729184400000,
            "filterTheaterId":53,
            "description": cleanTitle,
            "gameTypeId": "a56d1c3b08df436dbb774401f9a81a43",
            "hostId": "41602b8106804a898ee2976a29c3d114",
            "images": "https://img.youtube.com/vi/"+value.replace("/shorts/", "")+"/maxresdefault.jpg",
            "type":"CONTENT",
            "isPortrait":1
        })
    file_path = "M6.json"

    # Writing list to JSON file
    with open(file_path, "w") as json_file:
        json.dump(result, json_file)

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


def get_all_link(url):
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

    file_path = "linkOnePiece.json"

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

def setResultData():
    data = []
    title = []
    result = []
    with open('iframeOnePieceFinal2.json', 'r') as file:
        data = json.load(file)

    with open('titleOnePiece.json', 'r') as file:
        title = json.load(file)

    for idx, url in enumerate(data):
        arc = get_arc_by_episode(url["episode"])
        judul = next((episode["title"] for episode in title if episode["episode"] == url["episode"]), None)
        result.append({
            "title": url["episode"].zfill(3) + " - " + judul,
            "url":url["iframe"],
            "beginTime": 1729098000000,
            "endTime": 1729184400000,
            "filterTheaterId":filterId.get(arc),
            "description": url["episode"] + " - " + judul,
            "gameTypeId": "84b2dbb2186f40a2918de9080cb8e7a6",
            "hostId": "41602b8106804a898ee2976a29c3d114",
            "images": images.get(arc),
            "type":"CONTENT",
            "isPortrait":0
        })

    file_path = "OnePiece.json"

    # # Writing list to JSON file
    with open(file_path, "w") as json_file:
        json.dump(result, json_file)

    print("Profile data saved to data.json")

def insertDataToNevv(fileName, reverse):
    # API endpoint URL
    url = 'https://www.nevv.io/api/theater/pc/add'
    data = []
    with open(fileName, 'r') as file:
        data = json.load(file)

    if(reverse == True):
        data = data[::-1]

    for d in data:

        headers = {
            'X-Auth-Admin-Alif': '02hcj084hfpjPPHPpHJE',
            'Content-Type': 'application/json'
        }
        response = requests.post(url, json=d, headers=headers)

        if response.status_code == 200:
            print("Success")
        else:
            print("Failed:", response.status_code, response.text)

# Main script
if __name__ == "__main__":
    # cleanShorts()
    lists = []
    marapthon_urls = [
        "https://youtu.be/DR2bn0fmVrY?si=0AZq1kQozr0jguEm",
        "https://youtu.be/b5r32LNly-A?si=ewblQhOmZpJCtml5",
        "https://youtu.be/cThMQX8rzxE?si=Dzy4gh_MDUg6pSW2",
        "https://youtu.be/2oM9iDQL5Z4?si=K9HlFOgSInFiWD8v",
        "https://youtu.be/U3UVKDQKes4?si=NIzyoUJkG5hB73Np",
        "https://youtu.be/BqXeXsQpbr8?si=t3EzQvADBTBubt9a",
        "https://youtu.be/FN7jek1NvLc?si=fyD3kdR_xYoK_8TP",
        "https://youtu.be/SK0lVkQHnAM?si=JdNKDTpvB_knyoG_",
        "https://youtu.be/FKnPgteq8Ik?si=Q9HIB_Q0zTOE0wy2",
        "https://youtu.be/_2ew9s1L59g?si=tyZMQgGixd1krskO",
        "https://youtu.be/9WnWJIhM_yg?si=_dJtxE4J1-WfrjI9"
    ]


    # for url in marapthon_urls:
    #     lists.append(insertYoutubeVideos(url))

    # file_path = "MarathonS2.json"
    # # Writing list to JSON file
    # with open(file_path, "w") as json_file:
    #     json.dump(lists, json_file)


    insertDataToNevv("MarathonS2.json", False)

# cara run program scrapping
# source venv/bin/activate  
# python scrappingYoutube.py  
