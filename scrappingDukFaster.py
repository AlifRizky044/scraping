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
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from constant import *
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import urlparse, parse_qs, urljoin

from bs4 import BeautifulSoup

# Set up the webdriver
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
wait = WebDriverWait(driver, 12)
SIMPEG_BASE_URL = "https://bkpsdm.medan.go.id/simpeg/"

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

def appendManyToFile(file_path, data_list):
    if not data_list:
        return

    if os.path.exists(file_path):
        with open(file_path, "r") as json_file:
            try:
                existing_data = json.load(json_file)
            except json.JSONDecodeError:
                existing_data = []
    else:
        existing_data = []

    if isinstance(existing_data, list):
        existing_data.extend(data_list)
    else:
        existing_data = [existing_data] + data_list

    with open(file_path, "w") as json_file:
        json.dump(existing_data, json_file, indent=4)

def openRiwayatPage(menu_label):
    latest_li = wait.until(EC.element_to_be_clickable((By.XPATH, '//ul[@class="nav navbar-nav"]/li[last()]')))
    latest_li.click()
    target_menu = wait.until(EC.element_to_be_clickable((By.XPATH, f'//a[contains(text(), "{menu_label}")]')))
    target_menu.click()
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table.dataTable")))

def waitForPegawaiTable(profile_url, retries=3):
    for _ in range(retries):
        try:
            wait.until(EC.presence_of_element_located((By.NAME, "DataTables_Table_0_length")))
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'tr.even, tr.odd')))
            return
        except TimeoutException:
            # Keep original flow behavior: reload list page and retry.
            driver.get(profile_url)
            time.sleep(2)
    raise TimeoutException("Data pegawai table did not load after retries")

def scrappingAllDiklatStruktural():
    openRiwayatPage("Riwayat Diklat")

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
    openRiwayatPage("Riwayat Diklat")

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
    openRiwayatPage("Riwayat Jabatan")

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
    openRiwayatPage("Riwayat Pangkat")

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
    openRiwayatPage("Riwayat Pangkat")

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
    openRiwayatPage("Riwayat Pendidikan")

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
    openRiwayatPage("Riwayat Pendidikan")

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


def getSelectedText(select_element):
    if not select_element:
        return ""
    selected_option = select_element.find('option', selected=True)
    return selected_option.text.strip() if selected_option else ""

def getInputValue(soup, name):
    element = soup.find("input", {"name": name})
    return element.get("value", "") if element else ""

def buildRowPayload(row, profile_url):
    cells = [td.text.strip() for td in row.find_elements(By.TAG_NAME, "td")]
    if len(cells) < 8:
        return None

    detail_url = ""
    try:
        link = row.find_element(By.CSS_SELECTOR, "a.linkimage")
        detail_url = link.get_attribute("href") or ""
    except Exception:
        try:
            img = row.find_element(By.CSS_SELECTOR, 'img[title="Lanjut Untuk Memanajemen Data Pegawai"]')
            onclick = img.get_attribute("onclick") or ""
            url_match = re.search(r"'([^']+)'", onclick)
            if url_match:
                detail_url = url_match.group(1)
        except Exception:
            detail_url = ""

    if not detail_url:
        return None

    return {
        "detail_url": urljoin(profile_url, detail_url),
        "namaWithGelar": cells[1],
        "nip": cells[2].replace(" ", ""),
        "kedudukan": cells[3],
        "tempatTglLahir": cells[4],
        "golonganTerakhir": cells[5],
        "jabatanTerakhir": cells[6],
        "skpd": cells[7]
    }

def scrapeEmployee(detail_url, row_meta):
    driver.get(detail_url)
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

    try:
        ok_button = driver.find_element(By.ID, "popup_ok")
        ok_button.click()
    except NoSuchElementException:
        pass

    soup = BeautifulSoup(driver.page_source, 'html.parser')

    jenisKepegawaianVal = getSelectedText(soup.find('select', {'id': 'id_jenis_kepegawaian'}))
    kedudukanKepegawaianVal = getSelectedText(soup.find('select', {'id': 'id_kedudukan_kepegawaian'}))
    statusKepegawaianVal = getSelectedText(soup.find('select', {'id': 'id_status_kepegawaian'}))
    agamaVal = getSelectedText(soup.find('select', {'id': 'id_agama'}))
    statusPernikahanVal = getSelectedText(soup.find('select', {'id': 'id_status_pernikahan'}))
    jenisKelaminVal = getSelectedText(soup.find('select', {'id': 'id_jenis_kelamin'}))
    golDarahVal = getSelectedText(soup.find('select', {'id': 'id_golongan_darah'}))
    rambutVal = getSelectedText(soup.find('select', {'id': 'id_rambut'}))
    bentukMukaVal = getSelectedText(soup.find('select', {'id': 'id_bentuk_muka'}))
    warnaKulitVal = getSelectedText(soup.find('select', {'id': 'id_warna_kulit'}))

    nipValue = getInputValue(soup, "nip").replace(" ", "")
    nipLama = getInputValue(soup, "nip_lama")

    links = soup.find_all("a", class_="link_auto_panel")
    result = []
    for a in links:
        href = a.get("href", "")
        query = urlparse(href).query
        params = parse_qs(query)
        tipe = params.get("type", [None])[0]
        if tipe:
            result.append({
                "href": urljoin(SIMPEG_BASE_URL, href),
                "type": tipe
            })

    riwayatPangkat = ""
    riwayatJabatan = ""
    riwayatPendidikan = ""
    riwayatDiklatStruktural = ""
    riwayatDiklatLainnya = ""

    if "PNS" in row_meta["kedudukan"]:
        riwayatPangkat = scrappingAllPangkat()
        riwayatJabatan = scrappingAllJabatan()
        riwayatDiklatStruktural = scrappingAllDiklatStruktural()
        riwayatDiklatLainnya = scrappingAllDiklatLainnya()

    riwayatPendidikan = scrappingAllPendidikan()

    return {
        "nip": nipValue,
        "nipLama": nipLama,
        "kedudukanKepegawaian": kedudukanKepegawaianVal,
        "jenisKepegawaian": jenisKepegawaianVal,
        "statusKepegawaian": statusKepegawaianVal,
        "agama": agamaVal,
        "statusPernikahan": statusPernikahanVal,
        "jenisKelamin": jenisKelaminVal,
        "golDarah": golDarahVal,
        "rambut": rambutVal,
        "bentukMuka": bentukMukaVal,
        "warnaKulit": warnaKulitVal,
        "tempatLahir": getInputValue(soup, "tempat_lahir"),
        "tanggalLahir": getInputValue(soup, "tanggal_lahir"),
        "alamat": getInputValue(soup, "alamat"),
        "provinsi": getInputValue(soup, "id_provinsi"),
        "kota": getInputValue(soup, "id_kabupaten"),
        "kecamatan": getInputValue(soup, "id_kecamatan"),
        "kelurahan": getInputValue(soup, "id_kelurahan"),
        "rt": getInputValue(soup, "rt"),
        "rw": getInputValue(soup, "rw"),
        "kodePos": getInputValue(soup, "kode_pos"),
        "noTel": getInputValue(soup, "no_telp"),
        "noHp": getInputValue(soup, "no_hp"),
        "email": getInputValue(soup, "email"),
        "tinggi": getInputValue(soup, "tinggi"),
        "berat": getInputValue(soup, "berat"),
        "suku": getInputValue(soup, "id_suku"),
        "marga": getInputValue(soup, "marga"),
        "cacat": getInputValue(soup, "cacat_tubuh"),
        "ciriKhas": getInputValue(soup, "ciri_khas"),
        "hobi": getInputValue(soup, "hobi"),
        "nik": getInputValue(soup, "ktp"),
        "taspen": getInputValue(soup, "taspen"),
        "karpeg": getInputValue(soup, "no_karpeg"),
        "askes": getInputValue(soup, "no_askes"),
        "npwp": getInputValue(soup, "npwp"),
        "gelarDepan": getInputValue(soup, "gelar_depan"),
        "nama": getInputValue(soup, "nama_pegawai"),
        "gelarBelakang": getInputValue(soup, "gelar_belakang"),
        "namaWithGelar": row_meta["namaWithGelar"],
        "kedudukan": row_meta["kedudukan"],
        "tempatTglLahir": row_meta["tempatTglLahir"],
        "golonganTerakhir": row_meta["golonganTerakhir"],
        "jabatanTerakhir": row_meta["jabatanTerakhir"],
        "skpd": row_meta["skpd"],
        "riwayatDiklatLainnya": riwayatDiklatLainnya,
        "riwayatDiklatStruktural": riwayatDiklatStruktural,
        "riwayatJabatan": riwayatJabatan,
        "riwayatPendidikan": riwayatPendidikan,
        "riwayatPangkat": riwayatPangkat,
        "links": result
    }

# Function to scrape SIMPEG profile list
def scrape(profile_url, output_file="DUKPNSFULL.json", start_index=723, max_records=850, flush_every=20):
    driver.get(profile_url)

    username_input = wait.until(EC.presence_of_element_located((By.NAME, "username")))
    password_input = driver.find_element(By.NAME, "password")
    username_input.send_keys("admin_skpd_3182")
    password_input.send_keys("PemkoMedan12345678.")
    driver.find_element(By.XPATH, "//button[@type='submit']").click()

    time.sleep(5)
    driver.get(profile_url)

    buffer = []

    # Keep original flow: iterate rows by absolute index, recalculate page step each loop.
    for i in range(max_records):
        time.sleep(3)
        dropdown = Select(wait.until(EC.presence_of_element_located((By.NAME, "DataTables_Table_0_length"))))
        dropdown.select_by_value("100")

        time.sleep(1)
        next_button = wait.until(EC.presence_of_element_located((By.ID, "DataTables_Table_0_next")))
        index = i + start_index

        if index >= 100:
            steps = index // 100
            if "ui-state-disabled" not in next_button.get_attribute("class"):
                for _ in range(steps):
                    next_button = wait.until(EC.element_to_be_clickable((By.ID, "DataTables_Table_0_next")))
                    next_button.click()
                index -= steps * 100

        time.sleep(1)
        rows = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'tr.even, tr.odd')))

        try:
            row = rows[index]
            cells = [td.text.strip() for td in row.find_elements(By.TAG_NAME, "td")]

            namaWithGelar = cells[1]
            kedudukan = cells[3]
            tempatTglLahir = cells[4]
            golonganTerakhir = cells[5]
            jabatanTerakhir = cells[6]
            skpd = cells[7]

            img = row.find_element(By.CSS_SELECTOR, 'img[title="Lanjut Untuk Memanajemen Data Pegawai"]')
            driver.execute_script("arguments[0].scrollIntoView();", img)
            img.click()

            time.sleep(1)
            try:
                ok_button = driver.find_element(By.ID, "popup_ok")
                ok_button.click()
            except NoSuchElementException:
                pass

            time.sleep(3)

            soup = BeautifulSoup(driver.page_source, 'html.parser')

            jenisKepegawaianVal = getSelectedText(soup.find('select', {'id': 'id_jenis_kepegawaian'}))
            kedudukanKepegawaianVal = getSelectedText(soup.find('select', {'id': 'id_kedudukan_kepegawaian'}))
            statusKepegawaianVal = getSelectedText(soup.find('select', {'id': 'id_status_kepegawaian'}))
            agamaVal = getSelectedText(soup.find('select', {'id': 'id_agama'}))
            statusPernikahanVal = getSelectedText(soup.find('select', {'id': 'id_status_pernikahan'}))
            jenisKelaminVal = getSelectedText(soup.find('select', {'id': 'id_jenis_kelamin'}))
            golDarahVal = getSelectedText(soup.find('select', {'id': 'id_golongan_darah'}))
            rambutVal = getSelectedText(soup.find('select', {'id': 'id_rambut'}))
            bentukMukaVal = getSelectedText(soup.find('select', {'id': 'id_bentuk_muka'}))
            warnaKulitVal = getSelectedText(soup.find('select', {'id': 'id_warna_kulit'}))

            nipValue = getInputValue(soup, "nip").replace(" ", "")
            nipLama = getInputValue(soup, "nip_lama")

            links = soup.find_all("a", class_="link_auto_panel")
            result = []
            for a in links:
                href = a.get("href", "")
                query = urlparse(href).query
                params = parse_qs(query)
                tipe = params.get("type", [None])[0]
                if tipe:
                    result.append({
                        "href": urljoin(SIMPEG_BASE_URL, href),
                        "type": tipe
                    })

            riwayatPangkat = ""
            riwayatJabatan = ""
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
                "nipLama": nipLama,
                "kedudukanKepegawaian": kedudukanKepegawaianVal,
                "jenisKepegawaian": jenisKepegawaianVal,
                "statusKepegawaian": statusKepegawaianVal,
                "agama": agamaVal,
                "statusPernikahan": statusPernikahanVal,
                "jenisKelamin": jenisKelaminVal,
                "golDarah": golDarahVal,
                "rambut": rambutVal,
                "bentukMuka": bentukMukaVal,
                "warnaKulit": warnaKulitVal,
                "tempatLahir": getInputValue(soup, "tempat_lahir"),
                "tanggalLahir": getInputValue(soup, "tanggal_lahir"),
                "alamat": getInputValue(soup, "alamat"),
                "provinsi": getInputValue(soup, "id_provinsi"),
                "kota": getInputValue(soup, "id_kabupaten"),
                "kecamatan": getInputValue(soup, "id_kecamatan"),
                "kelurahan": getInputValue(soup, "id_kelurahan"),
                "rt": getInputValue(soup, "rt"),
                "rw": getInputValue(soup, "rw"),
                "kodePos": getInputValue(soup, "kode_pos"),
                "noTel": getInputValue(soup, "no_telp"),
                "noHp": getInputValue(soup, "no_hp"),
                "email": getInputValue(soup, "email"),
                "tinggi": getInputValue(soup, "tinggi"),
                "berat": getInputValue(soup, "berat"),
                "suku": getInputValue(soup, "id_suku"),
                "marga": getInputValue(soup, "marga"),
                "cacat": getInputValue(soup, "cacat_tubuh"),
                "ciriKhas": getInputValue(soup, "ciri_khas"),
                "hobi": getInputValue(soup, "hobi"),
                "nik": getInputValue(soup, "ktp"),
                "taspen": getInputValue(soup, "taspen"),
                "karpeg": getInputValue(soup, "no_karpeg"),
                "askes": getInputValue(soup, "no_askes"),
                "npwp": getInputValue(soup, "npwp"),
                "gelarDepan": getInputValue(soup, "gelar_depan"),
                "nama": getInputValue(soup, "nama_pegawai"),
                "gelarBelakang": getInputValue(soup, "gelar_belakang"),
                "namaWithGelar": namaWithGelar,
                "kedudukan": kedudukan,
                "tempatTglLahir": tempatTglLahir,
                "golonganTerakhir": golonganTerakhir,
                "jabatanTerakhir": jabatanTerakhir,
                "skpd": skpd,
                "riwayatDiklatLainnya": riwayatDiklatLainnya,
                "riwayatDiklatStruktural": riwayatDiklatStruktural,
                "riwayatJabatan": riwayatJabatan,
                "riwayatPendidikan": riwayatPendidikan,
                "riwayatPangkat": riwayatPangkat,
                "links": result
            }

            buffer.append(data)
            if len(buffer) >= flush_every:
                appendManyToFile(output_file, buffer)
                buffer = []

            print(f"[{i + 1}/{max_records}] {namaWithGelar}")
            driver.get(profile_url)

        except Exception as e:
            print(f"Error in row: {e}")

    if buffer:
        appendManyToFile(output_file, buffer)

    driver.close()
    return "success"

# Main script
if __name__ == "__main__":
    for i in range(1, 20):
        result = scrape('https://bkpsdm.medan.go.id/simpeg/?mod=data_pegawai')


# cara run program scrapping
# source venv/bin/activate  
# python scrappingDuk.py  
