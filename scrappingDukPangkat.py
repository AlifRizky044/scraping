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
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException
from constant import *
from webdriver_manager.chrome import ChromeDriverManager

from bs4 import BeautifulSoup

# Set up the webdriver
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

pattern = r"Episode (\d+(\.\d+)?|Spesial)"


def appendToFile(file_path, data):
    file_path = "DUKPNSPangkat.json"
    new_data = data  # assuming `result` is a dictionary or list

    # Step 1: Load existing data if file exists
    if os.path.exists(file_path):
        with open(file_path, "r") as json_file:
            try:
                existing_data = json.load(json_file)
            except json.JSONDecodeError:
                existing_data = []
    else:
        existing_data = []

    # Step 2: Append new data
    if isinstance(existing_data, list):
        existing_data.append(new_data)
    else:
        # if existing data is not a list, convert it to list
        existing_data = [existing_data, new_data]

    # Step 3: Save updated data
    with open(file_path, "w") as json_file:
        json.dump(existing_data, json_file, indent=4)


# Function to scrape a LinkedIn profile
def scrape(profile_url):
    driver.get(profile_url)
    time.sleep(14)
    # driver.get(profile_url)
    # time.sleep(5)
    # time.sleep(10) 

    # 3. Loop through each row and click the <img> tag inside
    for i in range(60):

        time.sleep(5)
        dropdown = Select(driver.find_element(By.NAME, "DataTables_Table_0_length"))

        # Select the option with value="100"
        dropdown.select_by_value("100")

        # 2. Find all <tr class="odd">
        time.sleep(1)

        next_button = driver.find_element(By.ID, "DataTables_Table_0_next")
        # if "ui-state-disabled" not in next_button.get_attribute("class"):
        next_button.click()
        next_button.click()
        time.sleep(1)

        # rows = driver.find_elements(By.CSS_SELECTOR, 'tr.even')

        rows = driver.find_elements(By.CSS_SELECTOR, 'tr.even, tr.odd')

        try:
            # Find the <img> tag within the row
            row = rows[i]
            img = row.find_element(By.CSS_SELECTOR, 'img[title="Lanjut Untuk Memanajemen Data Pegawai"]')
            
            # Scroll into view (optional, if needed)
            driver.execute_script("arguments[0].scrollIntoView();", img)
            
            # Click the image
            img.click()
            
            # Wait or handle what happens after the click (you may need to go back or wait for modal)
            time.sleep(5)


            latest_li = driver.find_element(By.XPATH, '//ul[@class="nav navbar-nav"]/li[last()]')
            latest_li.click()
            driver.find_element(By.XPATH, '//a[contains(text(), "Riwayat Pangkat")]').click()

            time.sleep(1)

            soup = BeautifulSoup(driver.page_source, 'html.parser')
            # Find the div with class 'panelcontainer'
            panel_div = soup.find('div', class_='panelcontainer')

            # Find the <h3> inside it
            h3_text = panel_div.find('h3').get_text(strip=True)

            # Extract the name
            name = h3_text.split('DATA RIWAYAT KEPANGKATAN ')[1].split(' (NIP')[0]
            nip_part = h3_text.split('(NIP :')[1].split(')')[0].replace(' ', '')

            statusVerifikasi = ""
            pangkat = ""
            tmt = ""
            noSk = ""
            pejabatPenandatangan = ""
            mkgTahun = ""
            mkgBulan = ""
            tglSk = ""
            file = ""
            catatan = ""
            # Find the last <tr> row
            table = soup.find('table', {'id': 'DataTables_Table_0'})
            last_row = table.tbody.find_all('tr')[-1]
            tds = last_row.find_all('td')


            statusVerifikasiBtn = tds[1].find('button', class_='btn-success')
            pangkat = tds[3].get_text(strip=True)
            tmt = tds[4].get_text(strip=True)
            noSk = tds[5].get_text(strip=True)
            tglSk = tds[6].get_text(strip=True)
            pejabatPenandatangan = tds[7].get_text(strip=True)
            mkgTahun = tds[8].get_text(strip=True)
            mkgBulan = tds[9].get_text(strip=True)

            a_tag = tds[11].find('a')

            # Get the href attribute
            file = a_tag['href'] if a_tag else ""
            catatan = tds[13].get_text(strip=True)


            if statusVerifikasiBtn:
                statusVerifikasi = "Terverifikasi"
            else:
                statusVerifikasi = "Belum Terverifikasi"

            data = {
                "name": name,
                "nip": nip_part,
                "statusVerifikasi": statusVerifikasi,
                "pangkat": pangkat,
                "tmt": tmt,
                "noSk": noSk,
                "tglSk": tglSk,
                "pejabatPenandatangan": pejabatPenandatangan,
                "mkgTahun": mkgTahun,
                "mkgBulan": mkgBulan,
                "file": "https://bkpsdm.medan.go.id/simpeg/" + file,
                "catatan": catatan
            }

            appendToFile("DUKPNSPangkat.json", data)


            # # Extract plain <td> text
            # values = [td.get_text(strip=True) for td in tds]

            # # Extract the <a> link and text (if any)
            # link = last_row.find('a')
            # if link:
            #     values.append(link.get_text(strip=True))
            #     values.append(link['href'])
            # else:
            #     values.append(None)
            #     values.append(None)

            # # Pad or truncate values to match custom_keys length
            # if len(values) < len(custom_keys):
            #     values += [None] * (len(custom_keys) - len(values))
            # elif len(values) > len(custom_keys):
            #     values = values[:len(custom_keys)]

            # Zip into a dictionary
            # row_data = dict(zip(custom_keys, values))



            # soup = BeautifulSoup(driver.page_source, 'html.parser')

            # table = soup.find("table", {"id":"DataTables_Table_0"})
            # oddColumn = table.find_all("tr", {"class":"odd"})
            # for t in oddColumn:
            #     print(t)
            #     tds = t.find_all("td")
            #     if tds:
            #         last_td = tds[-1]
            #         link = driver.find_element(By.CLASS_NAME, 'linkimage')
            #         link.click()
            # driver.back()
            driver.get(profile_url)
            
            # Optional: Navigate back if clicking takes you to a new page
            # driver.back()

        except Exception as e:
            print(f"Error in row: {e}")
    driver.close()
    return





    return "success"

# Main script
if __name__ == "__main__":
    for i in range(1, 20):
        result = scrape('https://bkpsdm.medan.go.id/simpeg/?mod=data_pegawai')


# cara run program scrapping
# source venv/bin/activate  
# python scrappingDukPangkat.py  
