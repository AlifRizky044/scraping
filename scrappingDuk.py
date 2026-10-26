import argparse
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
import itertools
import os
import re
import threading
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

pattern = r"Episode (\d+(\.\d+)?|Spesial)"
file_lock = threading.Lock()


def detect_browser():
    """Find Google Chrome without falling back to another browser."""
    custom_binary = os.getenv("CHROME_BINARY") or os.getenv("BROWSER_BINARY")
    if custom_binary:
        if not os.path.isfile(custom_binary):
            raise FileNotFoundError(
                f"CHROME_BINARY tidak ditemukan: {custom_binary}"
            )
        return custom_binary

    browser_candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        os.path.expanduser(
            "~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        ),
        (
            "/Applications/Google Chrome for Testing.app/Contents/MacOS/"
            "Google Chrome for Testing"
        ),
    ]

    for browser_binary in browser_candidates:
        if os.path.isfile(browser_binary):
            return browser_binary

    raise FileNotFoundError(
        "Google Chrome tidak ditemukan. Instal Google Chrome atau atur lokasinya "
        "melalui environment variable CHROME_BINARY."
    )


def create_driver(driver_path, browser_binary):
    """Create an isolated browser for one scraping worker."""
    options = webdriver.ChromeOptions()
    options.binary_location = browser_binary
    options.add_argument("--start-maximized")
    return webdriver.Chrome(service=Service(driver_path), options=options)


def appendToFile(file_path, data):
    # Every worker writes to the same JSON file, so the complete read/modify/write
    # operation must be protected from other threads.
    with file_lock:
        if os.path.exists(file_path):
            with open(file_path, "r") as json_file:
                try:
                    existing_data = json.load(json_file)
                except json.JSONDecodeError:
                    existing_data = []
        else:
            existing_data = []

        if isinstance(existing_data, list):
            existing_data.append(data)
        else:
            existing_data = [existing_data, data]

        with open(file_path, "w") as json_file:
            json.dump(existing_data, json_file, indent=4)


def scrappingAllDiklatStruktural(driver):
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

def scrappingAllDiklatLainnya(driver):
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

def scrappingAllJabatan(driver):
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
def scrappingAllPangkat(driver):
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
def scrappingLatestPangkat(driver):
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

def scrappingAllPendidikan(driver):
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

def scrappingLatestPendidikan(driver):
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


# Scrape the employee indexes assigned to one browser/worker.
def _scrape_indices(driver, profile_url, employee_indices, output_file, worker_id):
    driver.get(profile_url)

    time.sleep(5)

    # Find input fields and fill them
    username_input = driver.find_element(By.NAME, "username")
    password_input = driver.find_element(By.NAME, "password")

    username_input.send_keys("admin_skpd_3182")
    password_input.send_keys("PemkoMedan12345678.")

    # Find the button and click
    login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
    login_button.click()

    time.sleep(20)

    driver.get(profile_url)

    # time.sleep(20)
    # driver.get(profile_url)
    # time.sleep(5)
    # time.sleep(10) 

    # Loop through only the rows assigned to this worker.
    for employee_index in employee_indices:

        time.sleep(3)
        dropdown = Select(driver.find_element(By.NAME, "DataTables_Table_0_length"))

        # Select the option with value="100"
        dropdown.select_by_value("100")

        # 2. Find all <tr class="odd">
        time.sleep(1)
        next_button = driver.find_element(By.ID, "DataTables_Table_0_next")

        index = employee_index

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
                riwayatPangkat = scrappingAllPangkat(driver)
                riwayatJabatan = scrappingAllJabatan(driver)
                riwayatDiklatStruktural = scrappingAllDiklatStruktural(driver)
                riwayatDiklatLainnya = scrappingAllDiklatLainnya(driver)
            
            riwayatPendidikan = scrappingAllPendidikan(driver)

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

            appendToFile(output_file, data)
            print(f"Worker {worker_id}: data index {employee_index} selesai")
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
            print(f"Worker {worker_id}: error di index {employee_index}: {e}")


def _scrape_worker(
    profile_url,
    employee_indices,
    driver_path,
    browser_binary,
    output_file,
    worker_id,
):
    """Run one index chunk in an independent Selenium session."""
    driver = create_driver(driver_path, browser_binary)
    try:
        first_indexes = ", ".join(str(index) for index in employee_indices[:3])
        print(
            f"Worker {worker_id}: memproses index {first_indexes}, ... "
            f"sampai {employee_indices[-1]} ({len(employee_indices)} data)"
        )
        _scrape_indices(
            driver, profile_url, employee_indices, output_file, worker_id
        )
        return len(employee_indices)
    finally:
        driver.quit()


def _split_index_range(start_index, total_data, worker_count):
    """Distribute indexes round-robin: worker 1 gets loops 1, 5, 9, etc."""
    worker_count = min(worker_count, total_data)
    stop_index = start_index + total_data
    return [
        range(start_index + worker_number, stop_index, worker_count)
        for worker_number in range(worker_count)
    ]


def scrape(
    profile_url,
    workers=4,
    start_index=0,
    total_data=841,
    output_file="DUKPNSFULLapril.json",
):
    """Scrape employee data concurrently with one browser per worker."""
    if workers < 1:
        raise ValueError("Jumlah worker minimal 1")
    if total_data < 1:
        raise ValueError("Jumlah data minimal 1")

    # Resolve/install the matching driver once to avoid concurrent installations.
    browser_binary = detect_browser()
    driver_path = ChromeDriverManager().install()
    print(f"Browser yang digunakan: {browser_binary}")
    chunks = _split_index_range(start_index, total_data, workers)

    with ThreadPoolExecutor(max_workers=len(chunks)) as executor:
        futures = [
            executor.submit(
                _scrape_worker,
                profile_url,
                chunk,
                driver_path,
                browser_binary,
                output_file,
                worker_id,
            )
            for worker_id, chunk in enumerate(chunks, start=1)
        ]

        for future in as_completed(futures):
            future.result()

    print(f"Selesai memproses {total_data} index dengan {len(chunks)} worker")

# Main script
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scraping data pegawai secara paralel")
    parser.add_argument("--workers", type=int, default=4, help="Jumlah browser paralel")
    parser.add_argument("--start", type=int, default=0, help="Index awal pegawai")
    parser.add_argument("--total", type=int, default=841, help="Jumlah data")
    parser.add_argument(
        "--output", default="DUKPNSFULLjuli.json", help="Lokasi file output JSON"
    )
    args = parser.parse_args()

    scrape(
        "https://bkpsdm.medan.go.id/simpeg/?mod=data_pegawai",
        workers=args.workers,
        start_index=args.start,
        total_data=args.total,
        output_file=args.output,
    )


# cara run program scrapping
# source venv/bin/activate  
# python scrappingDuk.py  
