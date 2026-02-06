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

arcs = {
    "Romance Dawn": range(1, 4),  # Episode 1-3
    "Orange Town": range(4, 9),   # Episode 4-8
    "Syrup Village": range(9, 19),  # Episode 9-18
    "Baratie": range(19, 31),     # Episode 19-30
    "Arlong Park": range(31, 46), # Episode 31-45
    "Buggy Side Story": range(46, 48),  # Episode 46-47 (Filler Cover Story)
    "Logue Town": range(48, 54),  # Episode 48-53
    "Warship Island": range(54, 62),  # Episode 54-61 (Filler)
    "Reverse Mountain": range(62, 64),  # Episode 62-63
    "Whiskey Peak": range(64, 68),  # Episode 64-67
    "Coby and Helmeppo": range(68, 70),  # Episode 68-69 (Filler Cover Story)
    "Little Garden": range(70, 78),  # Episode 70-77
    "Drum Island": range(78, 92),  # Episode 78-91
    "Alabasta": range(92, 131),  # Episode 92-130
    "Post-Alabasta": range(131, 136),  # Episode 131-135 (Filler)
    "Goat Island": range(136, 139),  # Episode 136-138 (Filler)
    "Ruluka Island": range(139, 144),  # Episode 139-143 (Filler)
    "Jaya Island": range(144, 153),  # Episode 144-152
    "Skypiea": range(153, 196),  # Episode 153-195
    "G-8": range(196, 207),  # Episode 196-206 (Filler)
    "Long Ring Long Land": range(207, 220),  # Episode 207-219
    "Ocean’s Dream": range(220, 225),  # Episode 220-224 (Filler)
    "Foxy’s Return": range(225, 229),  # Episode 225-228 (Filler)
    "Water 7": range(229, 264),  # Episode 229-263
    "Enies Lobby": range(264, 313),  # Episode 264-312
    "Post-Enies Lobby": range(313, 326),  # Episode 313-325
    "Lovely Land": range(326, 337),  # Episode 326-336 (Filler)
    "Thriller Bark": range(337, 382),  # Episode 337-381
    "Spa Island": range(382, 385),  # Episode 382-384 (Filler)
    "Sabaody Archipelago": range(385, 408),  # Episode 385-407
    "Amazon Lily": range(408, 422),  # Episode 408-421
    "Impel Down (Part 1)": range(422, 426),  # Episode 422-425
    "Little East Blue": range(426, 430),  # Episode 426-429 (Filler)
    "Impel Down (Part 2)": range(430, 457),  # Episode 430-456
    "Marineford": range(457, 490),  # Episode 457-489
    "Post-War": range(490, 517),  # Episode 490-516
    "Return to Sabaody": range(517, 523),  # Episode 517-522
    "Fishman Island": range(523, 575),  # Episode 523-574
    "Z's Ambition": range(575, 579),  # Episode 575-578 (Filler)
    "Punk Hazard": range(579, 626),  # Episode 579-625
    "Caesar Retrieval": range(626, 629),  # Episode 626-628
    "Dressrosa": range(629, 747),  # Episode 629-746
    "Silver Mine": range(747, 751),  # Episode 747-750 (Filler)
    "Zou": range(751, 780),  # Episode 751-779
    "Marine Rookie": range(780, 783),  # Episode 780-782 (Filler)
    "Whole Cake Island": range(783, 878),  # Episode 783-877
    "Reverie": range(878, 892),  # Episode 878-891
    "Wano Country (Part 1)": range(892, 895),  # Episode 892-894
    "Cidre Guild": range(895, 897),  # Episode 895-896 (Filler)
    "Wano Country (Part 2)": range(897, 1029),  # Episode 897-1028
    "Uta’s Past": range(1029, 1031),  # Episode 1029-1030 (Special)
    "Wano Country (Part 3)": range(1031, 1071),  # Episode 1031-1070
    "Egghead Island": range(1071, 10**6)  # Episode 1071 onwards
}


filterId = {
    "Romance Dawn": 1,
    "Orange Town": 2,
    "Syrup Village": 3,
    "Baratie": 4,
    "Arlong Park": 5,
    "Buggy Side Story": 6,
    "Logue Town": 7,
    "Warship Island": 8,
    "Reverse Mountain": 9,
    "Whiskey Peak": 10,
    "Coby and Helmeppo": 11,
    "Little Garden": 12,
    "Drum Island": 13,
    "Alabasta": 14,
    "Post-Alabasta": 15,
    "Goat Island": 16,
    "Ruluka Island": 17,
    "Jaya Island": 18,
    "Skypiea": 19,
    "G-8": 20,
    "Long Ring Long Land": 21,
    "Ocean’s Dream": 22,
    "Foxy’s Return": 23,
    "Water 7": 24,
    "Enies Lobby": 25,
    "Post-Enies Lobby": 26,
    "Lovely Land": 27,
    "Thriller Bark": 28,
    "Spa Island": 29,
    "Sabaody Archipelago": 30,
    "Amazon Lily": 31,
    "Impel Down (Part 1)": 32,
    "Little East Blue": 33,
    "Impel Down (Part 2)": 32,
    "Marineford": 35,
    "Post-War": 36,
    "Return to Sabaody": 37,
    "Fishman Island": 38,
    "Z's Ambition": 39,
    "Punk Hazard": 40,
    "Caesar Retrieval": 41,
    "Dressrosa": 42,
    "Silver Mine": 43,
    "Zou": 44,
    "Marine Rookie": 49,
    "Whole Cake Island": 45,
    "Reverie": 46,
    "Wano Country (Part 1)": 47,
    "Cidre Guild": 50,
    "Wano Country (Part 2)": 47,
    "Uta’s Past": 51,
    "Wano Country (Part 3)": 47,
    "Egghead Island": 48
}



images = {
    "Romance Dawn": "https://nevv-1304168919.cos.ap-singapore.myqcloud.com/images/2024/10/15/1728958781144nevv_89bcs30tj.jpg",
    "Orange Town": "https://nevv-1304168919.cos.ap-singapore.myqcloud.com/images/2024/10/15/1728958824593nevv_9m318Qw26.jpg",
    "Syrup Village": "https://nevv-1304168919.cos.ap-singapore.myqcloud.com/images/2024/10/15/1728958905275nevv_X9Iy2TuH1.jpg",
    "Baratie": "https://nevv-1304168919.cos.ap-singapore.myqcloud.com/images/2024/10/15/1728979690526nevv_565pOEW03.jpg",
    "Arlong Park": "https://nevv-1304168919.cos.ap-singapore.myqcloud.com/images/2024/10/16/1729063041836nevv_2e8G1aD19.jpg",
    "Buggy Side Story": "https://nevv-1304168919.cos.ap-singapore.myqcloud.com/images/2024/10/17/1729144499235nevv_7q4HdL9VC.jpg",
    "Logue Town": "https://nevv-1304168919.cos.ap-singapore.myqcloud.com/images/2024/10/19/1729307323725nevv_6Y2TnXV86.jpg",
    "Warship Island": "https://nevv-1304168919.cos.ap-singapore.myqcloud.com/images/2024/10/19/1729307370800nevv_u66mDr9cq.jpg",
    "Reverse Mountain": "https://nevv-1304168919.cos.ap-singapore.myqcloud.com/images/2024/10/19/1729307399880nevv_Zk8sYeBe0.jpg",
    "Whiskey Peak": "https://nevv-1304168919.cos.ap-singapore.myqcloud.com/images/2024/10/19/1729307430404nevv_L1x6zzE64.jpg",
    "Coby and Helmeppo": "https://nevv-1304168919.cos.ap-singapore.myqcloud.com/images/2024/10/19/1729307453020nevv_9m074FBFZ.jpg",
    "Little Garden": "https://nevv-1304168919.cos.ap-singapore.myqcloud.com/images/2024/10/19/1729307483180nevv_P844F53EM.jpg",
    "Drum Island": "https://nevv-1304168919.cos.ap-singapore.myqcloud.com/images/2024/10/19/1729307505934nevv_1lVCNp8xg.jpg",
    "Alabasta": "https://nevv-1304168919.cos.ap-singapore.myqcloud.com/images/2024/10/19/1729307529166nevv_6YjLvtR02.jpg",
    "Post-Alabasta": "https://nevv-1304168919.cos.ap-singapore.myqcloud.com/images/2024/10/19/1729307556770nevv_gTj0028Wi.jpg",
    "Goat Island": "https://nevv-1304168919.cos.ap-singapore.myqcloud.com/images/2024/10/19/1729307580165nevv_860iMydUw.jpg",
    "Ruluka Island": "https://nevv-1304168919.cos.ap-singapore.myqcloud.com/images/2024/10/19/1729308127840nevv_7sFUl0I91.jpg",
    "Jaya Island": "https://nevv-1304168919.cos.ap-singapore.myqcloud.com/images/2024/10/19/1729308152075nevv_T9WX0915n.jpg",
    "Skypiea": "https://nevv-1304168919.cos.ap-singapore.myqcloud.com/images/2024/10/19/1729308178715nevv_HQ4f680KF.jpg",
    "G-8": "https://nevv-1304168919.cos.ap-singapore.myqcloud.com/images/2024/10/19/1729308204014nevv_uaK92040L.jpg",
    "Long Ring Long Land": "https://nevv-1304168919.cos.ap-singapore.myqcloud.com/images/2024/10/19/1729308242405nevv_054h37WA4.jpg",
    "Ocean’s Dream": "https://nevv-1304168919.cos.ap-singapore.myqcloud.com/images/2024/10/19/1729308267562nevv_ovA655246.jpg",
    "Foxy’s Return": "https://nevv-1304168919.cos.ap-singapore.myqcloud.com/images/2024/10/19/1729308292901nevv_k8iNu6pZP.jpg",
    "Water 7": "https://nevv-1304168919.cos.ap-singapore.myqcloud.com/images/2024/10/19/1729308332091nevv_l95HO6n41.jpg",
    "Enies Lobby": "https://nevv-1304168919.cos.ap-singapore.myqcloud.com/images/2024/10/19/1729308386181nevv_1rW50uGod.jpg",
    "Post-Enies Lobby": "https://nevv-1304168919.cos.ap-singapore.myqcloud.com/images/2024/10/19/1729308414395nevv_F8568rN1r.jpg",
    "Lovely Land": "https://nevv-1304168919.cos.ap-singapore.myqcloud.com/images/2024/10/19/1729308453308nevv_IzY95AbkY.jpg",
    "Thriller Bark": "https://nevv-1304168919.cos.ap-singapore.myqcloud.com/images/2024/10/19/1729308486590nevv_nPa4V74dX.jpg",
    "Spa Island": "https://nevv-1304168919.cos.ap-singapore.myqcloud.com/images/2024/10/19/1729308513183nevv_PkM002l94.jpg",
    "Sabaody Archipelago": "https://nevv-1304168919.cos.ap-singapore.myqcloud.com/images/2024/10/19/1729308547790nevv_C9r5692Pg.jpg",
    "Amazon Lily": "https://nevv-1304168919.cos.ap-singapore.myqcloud.com/images/2024/10/19/1729308571311nevv_VM7KNSie3.jpg",
    "Impel Down (Part 1)": "https://nevv-1304168919.cos.ap-singapore.myqcloud.com/images/2024/10/19/1729308605045nevv_mn3PX98j4.jpg",
    "Little East Blue": "https://nevv-1304168919.cos.ap-singapore.myqcloud.com/images/2024/10/19/1729308665273nevv_592P6689p.jpg",
    "Impel Down (Part 2)": "https://nevv-1304168919.cos.ap-singapore.myqcloud.com/images/2024/10/19/1729308605045nevv_mn3PX98j4.jpg",
    "Marineford": "https://nevv-1304168919.cos.ap-singapore.myqcloud.com/images/2024/10/19/1729308698704nevv_42Tt4lqF9.jpg",
    "Post-War": "https://nevv-1304168919.cos.ap-singapore.myqcloud.com/images/2024/10/19/1729308726772nevv_00sg2XCXp.jpg",
    "Return to Sabaody": "https://nevv-1304168919.cos.ap-singapore.myqcloud.com/images/2024/10/19/1729308758140nevv_oTb2FSN95.jpg",
    "Fishman Island": "https://nevv-1304168919.cos.ap-singapore.myqcloud.com/images/2024/10/19/1729308789885nevv_5a1L4Pp07.jpg",
    "Z's Ambition": "https://nevv-1304168919.cos.ap-singapore.myqcloud.com/images/2024/10/19/1729308815394nevv_4iEb9e5n5.jpg",
    "Punk Hazard": "https://nevv-1304168919.cos.ap-singapore.myqcloud.com/images/2024/10/19/1729308842230nevv_1SsQ1EBy6.jpg",
    "Caesar Retrieval": "https://nevv-1304168919.cos.ap-singapore.myqcloud.com/images/2024/10/19/1729308868282nevv_K6l606PZG.jpg",
    "Dressrosa": "https://nevv-1304168919.cos.ap-singapore.myqcloud.com/images/2024/10/19/1729308901194nevv_2UL26re01.jpg",
    "Silver Mine": "https://nevv-1304168919.cos.ap-singapore.myqcloud.com/images/2024/10/19/1729308928922nevv_P5E71C9oi.jpg",
    "Zou": "https://nevv-1304168919.cos.ap-singapore.myqcloud.com/images/2024/10/19/1729308953004nevv_p7DrMCU09.jpg",
    "Marine Rookie": "https://nevv-1304168919.cos.ap-singapore.myqcloud.com/images/2024/10/19/1729309343660nevv_9V3U775hb.jpg",
    "Whole Cake Island": "https://nevv-1304168919.cos.ap-singapore.myqcloud.com/images/2024/10/19/1729309369903nevv_y8c8Gw7ql.jpg",
    "Reverie": "https://nevv-1304168919.cos.ap-singapore.myqcloud.com/images/2024/10/19/1729309416349nevv_618t1B0MG.jpg",
    "Wano Country (Part 1)": "https://nevv-1304168919.cos.ap-singapore.myqcloud.com/images/2024/10/19/1729309474826nevv_265Yl3CV4.jpg",
    "Cidre Guild": "https://nevv-1304168919.cos.ap-singapore.myqcloud.com/images/2024/10/19/1729309532090nevv_522950z9b.jpg",
    "Wano Country (Part 2)": "https://nevv-1304168919.cos.ap-singapore.myqcloud.com/images/2024/10/19/1729309474826nevv_265Yl3CV4.jpg",
    "Uta’s Past": "https://nevv-1304168919.cos.ap-singapore.myqcloud.com/images/2024/10/19/1729309600796nevv_Re76N51gz.jpg",
    "Wano Country (Part 3)": "https://nevv-1304168919.cos.ap-singapore.myqcloud.com/images/2024/10/19/1729309474826nevv_265Yl3CV4.jpg",
    "Egghead Island": "https://nevv-1304168919.cos.ap-singapore.myqcloud.com/images/2024/10/19/1729309644499nevv_0TM21uQPf.jpg"
}

youtube_links = [
    "https://youtu.be/CLyvTw5hD_8?si=TZ-jP_qiekimkrNi",
    "https://youtu.be/wy6II0-3YeE?si=uGef41Whney-Vnim",
    "https://youtu.be/aUSxcAkRuHw?si=0DMGeJ01NpyyCbZX",
    "https://youtu.be/0w537TYOuqQ?si=vwMcnB2T6-dls5Qr",
    "https://youtu.be/Z5Sar6tBPDQ?si=v3abrJnfYAleCWLX",
    "https://youtu.be/a6LxYP-ufuc?si=D6yvDx3B1YYuTCLu",
    "https://youtu.be/CS_tFXInchQ?si=mzTn3qc96SepM15i",
    "https://youtu.be/yXGPLdpdC0I?si=wUcfaf85Zck_Lkus",
    "https://youtu.be/wI1iTm0FEzs?si=he-8DRBr-J90s3bM",
    "https://youtu.be/PMLogO2MQBU?si=aMM3b2OGreBjb1_J",
    "https://youtu.be/-_WQ4z8O664?si=9mILXBw33jdxhHCV",
    "https://youtu.be/7qp3iKk7qks?si=YiBo59hEz7dFQsOX",
    "https://youtu.be/tgjNu9Q7W0U?si=7BoInzC4P4ajDdbt",
    "https://youtu.be/51U1PoJLWbs?si=jQiOJ3xnptChcOUL",
    "https://youtu.be/8myAYNYRwp0?si=rsHu2cwrbU2sj6H4",
    "https://youtu.be/yQQeEk-zXM0?si=4zQNhmzvYu7dkF-5",
    "https://youtu.be/nUZfGQXTixU?si=tTmusK34j6Q8skab",
    "https://youtu.be/jKWQXWEMOfQ?si=RiIPJvAMBA35FTy2"
]

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
            "beginTime": 1729098000000,
            "endTime": 1729184400000,
            "filterTheaterId":52,
            "description": cleanTitle,
            "gameTypeId": "25dcdf00f13d41c18b934a58afdb1e16",
            "hostId": "86ad62c0f86b44bf930d9eea71aec6e5",
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

        # Sending POST request
        response = requests.post(url, json=d)

        # Checking the response
        if response.status_code == 200:
            print("Success")  # Print the response data
        else:
            print("Failed")  # Print error details

# Main script
if __name__ == "__main__":
    # cleanShorts()
    # scrapeYoutubeShorts("https://www.youtube.com/@MPLIndonesia/shorts")
    # scrapeYoutubeVideos("https://www.youtube.com/@YosepBudianto/videos")
    insertDataToNevv("Pokemon2.json", False)

    # scrapeAnime("https://myanimelist.net/anime/21/One_Piece/episode?offset=1100")
    # result = []
    # for item in youtube_links:
    #     result.append(insertYoutubeVideos(item))

    # file_path = "Pokemon2.json"

    # # Writing list to JSON file
    # with open(file_path, "w") as json_file:
    #     json.dump(result, json_file)

    # API endpoint URL
    # url = 'https://www.nevv.io/api/theater/pc/add'

    # for d in data:

    #     # Sending POST request
    #     response = requests.post(url, json=d)

    #     # Checking the response
    #     if response.status_code == 200:
    #         print("Success")  # Print the response data
    #     else:
    #         print("Failed")  # Print error details


    # listResult = []

    # with open('dataOnePiece2.json', 'r') as file:
    #     episode_urls = json.load(file)


    # with open('dataOnePieceiframe.json', 'r') as file:
    #     data = json.load(file)


    #     # print(f"Episode {idx + 1}: {url} belongs to {arc}")




    # data = []
    # with open('linkOnePiece.json', 'r') as file:
    #     data = json.load(file)

    # data = data[::-1]
    # for item in data:
    #     profile_data.append(scrape(item))

    # driver.quit()


    # dataOri = []
    # with open('iframeOnePieceFinal.json', 'r') as file:
    #     dataOri = json.load(file)


    # data = []
    # with open('iframeOnePiece.json', 'r') as file:
    #     data = json.load(file)

    # print(len(dataOri) == len(data))

    # Keywords to exclude
    # excluded_keywords = ["berkasdrive","mega","blogger",  "terabox",  "short.ink"]


    # priority = ["berkasdrive", "mega", "blogger", "terabox", "short.ink"]

    # result = []

    # Iterate through each episode group
    # for episode_group in data:
    #     selected_iframe = None
    #     # Check against priority list
    #     for priority_keyword in priority:
    #         for item in episode_group:
    #             if priority_keyword in item["iframe"]:
    #                 selected_iframe = item["iframe"]
    #                 break
    #         if selected_iframe:
    #             break
    #     # Fallback to any iframe if no priority match is found
    #     if not selected_iframe:
    #         selected_iframe = episode_group[0]["iframe"]  # Default to the first iframe in the list
    #     result.append({
    #         "episode":episode_group[0]["episode"],
    #         "iframe":selected_iframe
    #     })


    # # Filter the data
    # filtered_data = []
    # for sublist in data:
    #     found = any(any(keyword in item["iframe"] for keyword in excluded_keywords) for item in sublist)

    #     if found == False:
    #         filtered_data.append(sublist)

    # # Output the filtered data
    # print(filtered_data)

    # print(len(dataOri) == len(data))

    # for sublist in data:
    #     sublist[:] = [item for item in sublist if 'gdriveplayer' not in item['iframe']]

    # for sublist in data:
    #     sublist[:] = [item for item in sublist if '480p' not in item['type'] or item['episode'] in ['268', '277']]

    # # File path to save JSON data

    # file_path = "iframeOnePieceFinal.json"

    # # # Writing list to JSON file
    # with open(file_path, "w") as json_file:
    #     json.dump(result, json_file)

    # print("Profile data saved to data.json")

# cara run program scrapping
# source venv/bin/activate  
# python scrappingOnepiece.py  
