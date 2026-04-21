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
from urllib.parse import urlparse, parse_qs

from bs4 import BeautifulSoup

# Set up the webdriver
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

pattern = r"Episode (\d+(\.\d+)?|Spesial)"


def appendToFile(file_path, data):
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

def scrappingAllDiklatStruktural():
    latest_li = driver.find_element(By.XPATH, '//ul[@class="nav navbar-nav"]/li[last()]')
    latest_li.click()
    driver.find_element(By.XPATH, '//a[contains(text(), "Riwayat Diklat")]').click()

    time.sleep(1)

    soup = BeautifulSoup(driver.page_source, 'html.parser')

    # Find the table
    table = soup.find('table', {'id': 'DataTables_Table_0'})

    if not table or not table.tbody:
        return ""

    rows = table.tbody.find_all('tr')
    if not rows or rows[0].find('td', class_='dataTables_empty'):
        return ""

    # List to store all education records
    all_data = []

    # Loop through all rows instead of just the last one
    for row in rows:
        tds = row.find_all('td')

        # Extract data safely from each row
        statusVerifikasiBtn = tds[0].find('button', class_='btn-success')
        no = tds[1].get_text(strip=True)
        namaDiklat = tds[2].get_text(strip=True)
        tempatDiklat = tds[3].get_text(strip=True)
        penyelenggara = tds[4].get_text(strip=True)
        anggaran = tds[5].get_text(strip=True)
        mulai = tds[6].get_text(strip=True)
        selesai = tds[7].get_text(strip=True)
        noIjazah = tds[8].get_text(strip=True)
        tanggalIjazah = tds[9].get_text(strip=True)

        peringkat = tds[10].get_text(strip=True)
        # keteranganJabatan = tds[11].get_text(strip=True)

        # a_tag = tds[11].find('a')

        a_tag = tds[11].find('a')
        file = a_tag['href'] if a_tag else ""

        if file == "":
            a_tag = tds[12].find('a')
            file = a_tag['href'] if a_tag else ""

        # Get the href attribute
        # file = a_tag['href'] if a_tag else ""
        catatan = tds[14].get_text(strip=True)


        if statusVerifikasiBtn:
            statusVerifikasi = "Terverifikasi"
        else:
            statusVerifikasi = "Belum Terverifikasi"

        data = {
            "no": no,
            "statusVerifikasi": statusVerifikasi,
            "namaDiklat": namaDiklat,
            "tempatDiklat": tempatDiklat,
            "penyelenggara": penyelenggara,
            "anggaran": anggaran,
            "mulai": mulai,
            "selesai": selesai,
            "noIjazah": noIjazah,
            "tanggalIjazah": tanggalIjazah,
            "peringkat": peringkat,
            "file": "https://bkpsdm.medan.go.id/simpeg/" + file,
            "catatan": catatan
        }

        all_data.append(data)

    return all_data

def scrappingAllDiklatLainnya():
    latest_li = driver.find_element(By.XPATH, '//ul[@class="nav navbar-nav"]/li[last()]')
    latest_li.click()
    driver.find_element(By.XPATH, '//a[contains(text(), "Riwayat Diklat")]').click()

    time.sleep(1)

    soup = BeautifulSoup(driver.page_source, 'html.parser')

    # Find the table
    table = soup.find('table', {'id': 'DataTables_Table_1'})

    if not table or not table.tbody:
        return ""

    rows = table.tbody.find_all('tr')
    if not rows or rows[0].find('td', class_='dataTables_empty'):
        print("No data found")
        return ""

    # List to store all education records
    all_data = []

    # Loop through all rows instead of just the last one
    for row in rows:
        tds = row.find_all('td')

        # Extract data safely from each row
        statusVerifikasiBtn = tds[0].find('button', class_='btn-success')
        no = tds[1].get_text(strip=True)
        namaDiklat = tds[2].get_text(strip=True)
        tempatDiklat = tds[3].get_text(strip=True)
        penyelenggara = tds[4].get_text(strip=True)
        anggaran = tds[5].get_text(strip=True)
        mulai = tds[6].get_text(strip=True)
        selesai = tds[7].get_text(strip=True)
        noIjazah = tds[8].get_text(strip=True)
        tanggalIjazah = tds[9].get_text(strip=True)

        peringkat = tds[10].get_text(strip=True)
        # keteranganJabatan = tds[11].get_text(strip=True)

        # a_tag = tds[11].find('a')

        a_tag = tds[11].find('a')
        file = a_tag['href'] if a_tag else ""

        if file == "":
            a_tag = tds[12].find('a')
            file = a_tag['href'] if a_tag else ""

        # Get the href attribute
        # file = a_tag['href'] if a_tag else ""
        catatan = tds[14].get_text(strip=True)
        jenisDiklat = tds[15].get_text(strip=True)


        if statusVerifikasiBtn:
            statusVerifikasi = "Terverifikasi"
        else:
            statusVerifikasi = "Belum Terverifikasi"

        data = {
            "no": no,
            "statusVerifikasi": statusVerifikasi,
            "namaDiklat": namaDiklat,
            "tempatDiklat": tempatDiklat,
            "penyelenggara": penyelenggara,
            "anggaran": anggaran,
            "mulai": mulai,
            "selesai": selesai,
            "noIjazah": noIjazah,
            "tanggalIjazah": tanggalIjazah,
            "peringkat": peringkat,
            "file": "https://bkpsdm.medan.go.id/simpeg/" + file,
            "catatan": catatan,
            "jenisDiklat": jenisDiklat
        }

        all_data.append(data)

    return all_data

def scrappingAllJabatan():
    latest_li = driver.find_element(By.XPATH, '//ul[@class="nav navbar-nav"]/li[last()]')
    latest_li.click()
    driver.find_element(By.XPATH, '//a[contains(text(), "Riwayat Jabatan")]').click()

    time.sleep(1)

    soup = BeautifulSoup(driver.page_source, 'html.parser')

    # Find the table
    table = soup.find('table', {'id': 'DataTables_Table_0'})

    if not table or not table.tbody:
        return ""

    rows = table.tbody.find_all('tr')
    if not rows or rows[0].find('td', class_='dataTables_empty'):
        return ""

    # List to store all education records
    all_data = []

    # Loop through all rows instead of just the last one
    for row in rows:
        tds = row.find_all('td')

        # Extract data safely from each row
        statusVerifikasiBtn = tds[2].find('button', class_='btn-success')
        no = tds[1].get_text(strip=True)
        tipeJabatan = tds[3].get_text(strip=True)
        jabatan = tds[4].get_text(strip=True)
        jenjang = tds[5].get_text(strip=True)
        eselon = tds[6].get_text(strip=True)
        skpd = tds[7].get_text(strip=True)
        tmt = tds[8].get_text(strip=True)
        tmtSk = tds[9].get_text(strip=True)
        pejabatPenetapan = tds[10].get_text(strip=True)
        keteranganJabatan = tds[11].get_text(strip=True)

        # a_tag = tds[11].find('a')

        a_tag = tds[12].find('a')
        file = a_tag['href'] if a_tag else ""

        if file == "":
            a_tag = tds[13].find('a')
            file = a_tag['href'] if a_tag else ""

        # Get the href attribute
        # file = a_tag['href'] if a_tag else ""
        catatan = tds[15].get_text(strip=True)


        if statusVerifikasiBtn:
            statusVerifikasi = "Terverifikasi"
        else:
            statusVerifikasi = "Belum Terverifikasi"

        data = {
            "no": no,
            "statusVerifikasi": statusVerifikasi,
            "tipeJabatan": tipeJabatan,
            "tmt": tmt,
            "jabatan": jabatan,
            "jenjang": jenjang,
            "eselon": eselon,
            "skpd": skpd,
            "tmtSk": tmtSk,
            "pejabatPenetapan": pejabatPenetapan,
            "keteranganJabatan": keteranganJabatan,
            "file": "https://bkpsdm.medan.go.id/simpeg/" + file,
            "catatan": catatan
        }

        all_data.append(data)

    return all_data
def scrappingAllPangkat():
    latest_li = driver.find_element(By.XPATH, '//ul[@class="nav navbar-nav"]/li[last()]')
    latest_li.click()
    driver.find_element(By.XPATH, '//a[contains(text(), "Riwayat Pangkat")]').click()

    time.sleep(1)

    soup = BeautifulSoup(driver.page_source, 'html.parser')

    # Find the table
    table = soup.find('table', {'id': 'DataTables_Table_0'})

    if not table or not table.tbody:
        return ""

    rows = table.tbody.find_all('tr')
    if not rows or rows[0].find('td', class_='dataTables_empty'):
        return ""

    # List to store all education records
    all_data = []

    # Loop through all rows instead of just the last one
    for row in rows:
        tds = row.find_all('td')

        # Extract data safely from each row
        statusVerifikasiBtn = tds[1].find('button', class_='btn-success')
        no = tds[2].get_text(strip=True)
        pangkat = tds[3].get_text(strip=True)
        tmt = tds[4].get_text(strip=True)
        noSk = tds[5].get_text(strip=True)
        tglSk = tds[6].get_text(strip=True)
        pejabatPenandatangan = tds[7].get_text(strip=True)
        mkgTahun = tds[8].get_text(strip=True)
        mkgBulan = tds[9].get_text(strip=True)

        # a_tag = tds[11].find('a')

        a_tag = tds[10].find('a')
        file = a_tag['href'] if a_tag else ""

        if file == "":
            a_tag = tds[11].find('a')
            file = a_tag['href'] if a_tag else ""

        # Get the href attribute
        # file = a_tag['href'] if a_tag else ""
        catatan = tds[13].get_text(strip=True)


        if statusVerifikasiBtn:
            statusVerifikasi = "Terverifikasi"
        else:
            statusVerifikasi = "Belum Terverifikasi"

        data = {
            "no": no,
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

        all_data.append(data)

    return all_data
def scrappingLatestPangkat():
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

    return data

def scrappingAllPendidikan():
    latest_li = driver.find_element(By.XPATH, '//ul[@class="nav navbar-nav"]/li[last()]')
    latest_li.click()
    driver.find_element(By.XPATH, '//a[contains(text(), "Riwayat Pendidikan")]').click()

    time.sleep(1)

    soup = BeautifulSoup(driver.page_source, 'html.parser')

    # Find the table
    table = soup.find('table', {'id': 'DataTables_Table_0'})

    if not table or not table.tbody:
        return ""

    rows = table.tbody.find_all('tr')
    if not rows or rows[0].find('td', class_='dataTables_empty'):
        return ""

    # List to store all education records
    all_education_data = []

    # Loop through all rows instead of just the last one
    for row in rows:
        tds = row.find_all('td')

        # Extract data safely from each row
        statusVerifikasiBtn = tds[1].find('button', class_='btn-success')
        tingkatPendidikan = tds[2].get_text(strip=True)
        detailPendidikan = tds[3].get_text(strip=True)
        namaSekolah = tds[4].get_text(strip=True)
        tempat = tds[5].get_text(strip=True)
        jurusan = tds[6].get_text(strip=True)
        namaKepala = tds[7].get_text(strip=True)
        nomorIjazah = tds[8].get_text(strip=True)
        tanggalIjazah = tds[9].get_text(strip=True)
        ipk = tds[10].get_text(strip=True)

        a_tag = tds[11].find('a')
        file = a_tag['href'] if a_tag else ""

        if file == "":
            a_tag = tds[12].find('a')
            file = a_tag['href'] if a_tag else ""

        statusVerifikasi = "Terverifikasi" if statusVerifikasiBtn else "Belum Terverifikasi"

        data = {
            "statusVerifikasi": statusVerifikasi,
            "tingkatPendidikan": tingkatPendidikan,
            "detailPendidikan": detailPendidikan,
            "namaSekolah": namaSekolah,
            "tempat": tempat,
            "jurusan": jurusan,
            "namaKepala": namaKepala,
            "nomorIjazah": nomorIjazah,
            "tanggalIjazah": tanggalIjazah,
            "ipk": ipk,
            "file": f"https://bkpsdm.medan.go.id/simpeg/{file}" if file else ""
        }

        all_education_data.append(data)

    return all_education_data

def scrappingLatestPendidikan():
    """
    Get only the latest (most recent) education record
    Returns a single education record object or empty dict if no data
    """
    latest_li = driver.find_element(By.XPATH, '//ul[@class="nav navbar-nav"]/li[last()]')
    latest_li.click()
    driver.find_element(By.XPATH, '//a[contains(text(), "Riwayat Pendidikan")]').click()

    time.sleep(1)

    soup = BeautifulSoup(driver.page_source, 'html.parser')

    # Find the table
    table = soup.find('table', {'id': 'DataTables_Table_0'})

    if not table or not table.tbody:
        return ""

    rows = table.tbody.find_all('tr')
    if not rows or rows[0].find('td', class_='dataTables_empty'):
        return ""

    # Get only the last row (latest education record)
    last_row = rows[-1]
    tds = last_row.find_all('td')
    
    # Skip if row doesn't have enough columns
    if len(tds) < 12:
        return ""

    # Extract data safely from the last row
    statusVerifikasiBtn = tds[1].find('button', class_='btn-success')
    tingkatPendidikan = tds[2].get_text(strip=True)
    detailPendidikan = tds[3].get_text(strip=True)
    namaSekolah = tds[4].get_text(strip=True)
    tempat = tds[5].get_text(strip=True)
    jurusan = tds[6].get_text(strip=True)
    namaKepala = tds[7].get_text(strip=True)
    nomorIjazah = tds[8].get_text(strip=True)
    tanggalIjazah = tds[9].get_text(strip=True)
    ipk = tds[10].get_text(strip=True)

    a_tag = tds[11].find('a')
    file = a_tag['href'] if a_tag else ""

    if file == "":
        a_tag = tds[12].find('a')
        file = a_tag['href'] if a_tag else ""

    statusVerifikasi = "Terverifikasi" if statusVerifikasiBtn else "Belum Terverifikasi"

    data = {
        "statusVerifikasi": statusVerifikasi,
        "tingkatPendidikan": tingkatPendidikan,
        "detailPendidikan": detailPendidikan,
        "namaSekolah": namaSekolah,
        "tempat": tempat,
        "jurusan": jurusan,
        "namaKepala": namaKepala,
        "nomorIjazah": nomorIjazah,
        "tanggalIjazah": tanggalIjazah,
        "ipk": ipk,
        "file": f"https://bkpsdm.medan.go.id/simpeg/{file}" if file else ""
    }

    return data


# Function to scrape a LinkedIn profile
def scrape(profile_url):
    
    driver.get(profile_url)

    # Find input fields and fill them
    username_input = driver.find_element(By.NAME, "username")
    password_input = driver.find_element(By.NAME, "password")

    username_input.send_keys("admin_skpd_3182")
    password_input.send_keys("PemkoMedan12345678.")

    # Find the button and click
    login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
    login_button.click()

    time.sleep(5)

    driver.get(profile_url)

    # time.sleep(20)
    # driver.get(profile_url)
    # time.sleep(5)
    # time.sleep(10) 

    # 3. Loop through each row and click the <img> tag inside
    for i in range(842):

        time.sleep(3)
        dropdown = Select(driver.find_element(By.NAME, "DataTables_Table_0_length"))

        # Select the option with value="100"
        dropdown.select_by_value("100")

        # 2. Find all <tr class="odd">
        time.sleep(1)
        next_button = driver.find_element(By.ID, "DataTables_Table_0_next")

        index = i + 750

        if index >= 100:
            steps = index // 100  # contoh: 350 -> 3
            if "ui-state-disabled" not in next_button.get_attribute("class"):
                for _ in range(steps):
                    next_button.click()
                index -= steps * 100


        # if((index) >= 100 and (index) < 200):
        #     if "ui-state-disabled" not in next_button.get_attribute("class"):
        #         next_button.click()
        #         index = index - 100
        #         # next_button.click()
        #         # next_button.click()
        # elif((index) >= 200 and (index) < 300):
        #     if "ui-state-disabled" not in next_button.get_attribute("class"):
        #         next_button.click()
        #         next_button.click()
        #         index = index - 200

        #         # next_button.click()
        # elif((index) >= 300):
        #     if "ui-state-disabled" not in next_button.get_attribute("class"):
        #         next_button.click()
        #         next_button.click()
        #         next_button.click()
        #         index = index - 300


        time.sleep(1)

        rows = driver.find_elements(By.CSS_SELECTOR, 'tr.even, tr.odd')


        try:
            # Find the <img> tag within the row
            row = rows[index]
            cells = [td.text.strip() for td in row.find_elements(By.TAG_NAME, "td")]

            namaWithGelar = cells[1]
            nip = cells[2].replace(" ", "")
            kedudukan = cells[3]
            tempatTglLahir = cells[4]
            golonganTerakhir = cells[5]
            jabatanTerakhir = cells[6]
            skpd = cells[7]
            # pendidikanTerakhir = cells[8]

            img = row.find_element(By.CSS_SELECTOR, 'img[title="Lanjut Untuk Memanajemen Data Pegawai"]')
            
            # Scroll into view (optional, if needed)
            driver.execute_script("arguments[0].scrollIntoView();", img)
            
            # Click the image
            img.click()

            time.sleep(1)

            try:
                # cek apakah popup OK ada
                ok_button = driver.find_element(By.ID, "popup_ok")
                ok_button.click()
                print("Popup OK diklik")
            except NoSuchElementException:
                print("Tidak ada popup, lanjut proses")

            # if(namaWithGelar == "ERLINA MEGASARI HABEAHAN, SS"):
            #     popup = driver.find_element(By.ID, "popup_ok")

            #     if popup:
            #         popup.click()

            # Wait or handle what happens after the click (you may need to go back or wait for modal)
            time.sleep(3)

            soup = BeautifulSoup(driver.page_source, 'html.parser')
            nip = soup.find("input", {"name":"nip"})
            nipLama = soup.find("input", {"name":"nip_lama"})

            jenisKepegawaianVal = ""
            kedudukanKepegawaianVal = ""
            statusKepegawaianVal = ""
            agamaVal = ""
            golDarahVal = ""
            jenisKelaminVal = ""
            rambutVal = ""
            bentukMukaVal = ""
            warnaKulitVal = ""
            statusPernikahanVal = ""


            jenisKepegawaian = soup.find('select', {'id': 'id_jenis_kepegawaian'})
            # Find the selected option
            selected_option = jenisKepegawaian.find('option', selected=True)
            # Get the text
            if selected_option:
                jenisKepegawaianVal = selected_option.text.strip()

            kedudukanKepegawaian = soup.find('select', {'id': 'id_kedudukan_kepegawaian'})
            # Find the selected option
            selected_option = kedudukanKepegawaian.find('option', selected=True)
            # Get the text
            if selected_option:
                kedudukanKepegawaianVal = selected_option.text.strip()

            statusKepegawaian = soup.find('select', {'id': 'id_status_kepegawaian'})
            # Find the selected option
            selected_option = statusKepegawaian.find('option', selected=True)
            # Get the text
            if selected_option:
                statusKepegawaianVal = selected_option.text.strip()

            agama = soup.find('select', {'id': 'id_agama'})
            # Find the selected option
            selected_option = agama.find('option', selected=True)
            # Get the text
            if selected_option:
                agamaVal = selected_option.text.strip()

            statusPernikahan = soup.find('select', {'id': 'id_status_pernikahan'})
            # Find the selected option
            selected_option = statusPernikahan.find('option', selected=True)
            # Get the text
            if selected_option:
                statusPernikahanVal = selected_option.text.strip()

            jenisKelamin = soup.find('select', {'id': 'id_jenis_kelamin'})
            # Find the selected option
            selected_option = jenisKelamin.find('option', selected=True)
            # Get the text
            if selected_option:
                jenisKelaminVal = selected_option.text.strip()

            golDarah = soup.find('select', {'id': 'id_golongan_darah'})
            # Find the selected option
            selected_option = golDarah.find('option', selected=True)
            # Get the text
            if selected_option:
                golDarahVal = selected_option.text.strip()

            rambut = soup.find('select', {'id': 'id_rambut'})
            # Find the selected option
            selected_option = rambut.find('option', selected=True)
            # Get the text
            if selected_option:
                rambutVal = selected_option.text.strip()

            bentukMuka = soup.find('select', {'id': 'id_bentuk_muka'})
            # Find the selected option
            selected_option = bentukMuka.find('option', selected=True)
            # Get the text
            if selected_option:
                bentukMukaVal = selected_option.text.strip()

            warnaKulit = soup.find('select', {'id': 'id_warna_kulit'})
            # Find the selected option
            selected_option = warnaKulit.find('option', selected=True)
            # Get the text
            if selected_option:
                warnaKulitVal = selected_option.text.strip()
            tempatLahir = soup.find("input", {"name": "tempat_lahir"})
            tanggalLahir = soup.find("input", {"name": "tanggal_lahir"})
            alamat = soup.find("input", {"name": "alamat"})
            provinsi = soup.find("input", {"name": "id_provinsi"})
            kota = soup.find("input", {"name": "id_kabupaten"})
            kecamatan = soup.find("input", {"name": "id_kecamatan"})
            kelurahan = soup.find("input", {"name": "id_kelurahan"})
            rt = soup.find("input", {"name": "rt"})
            rw = soup.find("input", {"name": "rw"})
            kodePos = soup.find("input", {"name": "kode_pos"})
            noTel = soup.find("input", {"name": "no_telp"})
            noHp = soup.find("input", {"name": "no_hp"})
            email = soup.find("input", {"name": "email"})
            tinggi = soup.find("input", {"name": "tinggi"})
            berat = soup.find("input", {"name": "berat"})
            suku = soup.find("input", {"name": "id_suku"})
            marga = soup.find("input", {"name": "marga"})
            cacat = soup.find("input", {"name": "cacat_tubuh"})
            ciriKhas = soup.find("input", {"name": "ciri_khas"})
            hobi = soup.find("input", {"name": "hobi"})
            nik = soup.find("input", {"name":"ktp"})
            taspen = soup.find("input", {"name":"taspen"})
            karpeg = soup.find("input", {"name":"no_karpeg"})
            askes = soup.find("input", {"name":"no_askes"})
            npwp = soup.find("input", {"name":"npwp"})
            gelarDepan = soup.find("input", {"name": "gelar_depan"})
            nama = soup.find("input", {"name": "nama_pegawai"})
            gelarBelakang = soup.find("input", {"name": "gelar_belakang"})
            nipValue = nip.get("value").replace(' ', '')

            links = soup.find_all("a", class_="link_auto_panel")

            result = []
            for a in links:
                href = a["href"]

                query = urlparse(href).query
                params = parse_qs(query)

                # id_pegawai = params.get("id_pegawai", [None])[0]
                tipe = params.get("type", [None])[0]

                # hanya simpan kalau ada type
                if tipe:
                    result.append({
                        "href": "https://bkpsdm.medan.go.id/simpeg/" + href,
                        "type": tipe
                    })

            riwayatPangkat = ""
            riwayatJabatan = ""
            riwayatPendidikan = ""
            riwayatDiklatStruktural = ""
            riwayatDiklatLainnya = ""
            if "PNS" in kedudukan:
                riwayatPangkat = scrappingAllPangkat()
                riwayatJabatan = scrappingAllJabatan()
                riwayatDiklatStruktural = scrappingAllDiklatStruktural()
                riwayatDiklatLainnya = scrappingAllDiklatLainnya()
            
            riwayatPendidikan = scrappingAllPendidikan()

            data = {
                "nip": nipValue,
                "nipLama": nipLama.get("value"),
                "kedudukanKepegawaian": kedudukanKepegawaianVal,
                "jenisKepegawaian":jenisKepegawaianVal,
                "statusKepegawaian": statusKepegawaianVal,
                "agama": agamaVal,
                "statusPernikahan": statusPernikahanVal,
                "jenisKelamin": jenisKelaminVal,
                "golDarah": golDarahVal,
                "rambut": rambutVal,
                "bentukMuka": bentukMukaVal,
                "warnaKulit": warnaKulitVal,
                "tempatLahir": tempatLahir.get("value"),
                "tanggalLahir": tanggalLahir.get("value"),
                "alamat": alamat.get("value"),
                "provinsi": provinsi.get("value"),
                "kota": kota.get("value"),
                "kecamatan": kecamatan.get("value"),
                "kelurahan": kelurahan.get("value"),
                "rt": rt.get("value"),
                "rw": rw.get("value"),
                "kodePos": kodePos.get("value"),
                "noTel": noTel.get("value"),
                "noHp": noHp.get("value"),
                "email": email.get("value"),
                "tinggi": tinggi.get("value"),
                "berat": berat.get("value"),
                "suku": suku.get("value"),
                "marga": marga.get("value"),
                "cacat": cacat.get("value"),
                "ciriKhas": ciriKhas.get("value"),
                "hobi": hobi.get("value"),
                "nik": nik.get("value"),
                "taspen": taspen.get("value"),
                "karpeg": karpeg.get("value"),
                "askes": askes.get("value"),
                "npwp": npwp.get("value"),
                "gelarDepan": gelarDepan.get("value"),
                "nama": nama.get("value"),
                "gelarBelakang": gelarBelakang.get("value"),
                "namaWithGelar":namaWithGelar,
                "kedudukan":kedudukan,
                "tempatTglLahir":tempatTglLahir,
                "golonganTerakhir":golonganTerakhir,
                "jabatanTerakhir":jabatanTerakhir,
                "skpd":skpd,
                "riwayatDiklatLainnya":riwayatDiklatLainnya,
                "riwayatDiklatStruktural":riwayatDiklatStruktural,
                "riwayatJabatan":riwayatJabatan,
                "riwayatPendidikan":riwayatPendidikan,
                "riwayatPangkat":riwayatPangkat,
                "links": result
            }

            appendToFile("DUKPNSFULLapril.json", data)
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
# python scrappingDuk.py  
