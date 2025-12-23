import os
import time
import json
import pandas as pd
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

# Function to log in to LinkedIn
def login_to_linkedin(url):
    driver.get(url)
    time.sleep(5)

    signInBtn = driver.find_element(By.CSS_SELECTOR, "[data-tracking-control-name='public_profile_contextual-sign-in-modal_sign-in-modal_outlet-button']")
    signInBtn.click()
    
    email_input = driver.find_element(By.ID, "public_profile_contextual-sign-in_sign-in-modal_session_key")
    password_input = driver.find_element(By.ID, "public_profile_contextual-sign-in_sign-in-modal_session_password")
    
    driver.execute_script("arguments[0].value = arguments[1];", email_input, "alif171401044@gmail.com")
    driver.execute_script("arguments[0].value = arguments[1];", password_input, "Since2000.")
    # email_input.send_keys("alif171401044@gmail.com")
    # password_input.send_keys(password)
    password_input.send_keys(Keys.RETURN)
    
    time.sleep(20)  # Wait for the login to complete

def scrape_details(profile_url, idBtn, id):
    try:
        experience_btn = driver.find_element(By.ID, idBtn)
        experience_btn.click()
        driver.get(profile_url)

        time.sleep(5) 
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        uls = soup.find('div', {"class":'scaffold-finite-scroll__content'})
        job_titles = []
        if(uls):
            ul_elements = uls.find_all('ul')
            for ul in ul_elements:
                li_elements = ul.find_all('li')
                for li in li_elements:
                    span = li.select("div.display-flex.align-items-center.mr1.t-bold")
                    ed = ""
                    ed = li.find("span", {"class":'t-14 t-normal'})

                    if(len(span) > 0):
                        job_title = span[0].find('span', {"class":'visually-hidden'}).get_text().strip()
                        if(ed):
                            job_titles.append(job_title+" "+ed.get_text().strip())
                        # elif(id == "experience"):
                        #     job_titles.append(job_title)



        

        return job_titles
    except NoSuchElementException:
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        parent_elements = soup.find_all('section', class_='artdeco-card')

        institutions = []

        for parent_element in parent_elements:
            child_element = parent_element.find('div', {"id":id})
            if child_element:
                li_elements = parent_element.find('ul').find_all('li')
                for li in li_elements:
                    institution_span = li.find('div', class_='t-bold')
                    ed = ""
                    ed = li.find("span", {"class":'t-14 t-normal'})
                    if institution_span:
                        if(ed):
                            span = institution_span.find('span', class_='visually-hidden')
                            edu = ed.find('span', class_='visually-hidden')
                            if(span and edu):
                                institutions.append(span.text.strip()+" "+edu.text.strip())
                        # elif(id == "experience"):
                        #     span = institution_span.find('span', class_='visually-hidden')
                        #     if(span):
                        #         institutions.append(span.text.strip())

                break
        
        return institutions


# Function to scrape a LinkedIn profile
def scrape_linkedin_profile(profile_url):
    driver.get(profile_url)
    time.sleep(5)

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    
    # ambil nama
    name_div = soup.find('h1', {'class': 'text-heading-xlarge'}).get_text().strip()
    # if name_div:
    #     name = name_div.find('h1').get_text().strip()
    # else:
    #     name = None
    
    # Example: Extract current position
    # Find the <ul> element

    keahlian = ""
    skills = ""

    ul_element = soup.find('ul', class_='pvs-list--padded')
    li_element = None

    if(ul_element):
        li_element = ul_element.find('li')

    if(li_element):
        # ambil skills
        skills_span = li_element.find('div', class_='display-flex align-items-center t-14 t-normal')
        if(skills_span):
            skill_text = skills_span.find('span', {"class":'visually-hidden'})
            if(skill_text):
                skills = skill_text.get_text().strip()

    #ambil keahlian
    keahlian = soup.find('div', {'class': 'text-body-medium break-words'}).get_text().strip()

    #ambil pengalaman
    job_titles = scrape_details(profile_url+"/details/experience/", "navigation-index-see-all-experiences", "experience")

    driver.get(profile_url)
    time.sleep(5)

    #ambil pendidikan
    pendidikan = scrape_details(profile_url+"/details/education/", "navigation-index-see-all-education", "education")

    driver.get(profile_url)
    time.sleep(5) 

    #ambil certifikat kalau skill tidak ada di list
    if(skills == ""):
        skills = scrape_details(profile_url+"/details/certifications/", "navigation-index-see-all-licenses-and-certifications", "licenses_and_certifications")

    profile_data = {
        "Name": name_div,
        "Skills": skills,
        "Keahlian": keahlian,
        "Experience":job_titles,
        "Pendidikan":pendidikan
    }
    
    return profile_data

# Main script
if __name__ == "__main__":
    profile_url = linkedin_urls[0]
    print(profile_url)
    login_to_linkedin(profile_url)

    profile_data = []

    # profile_data.append(scrape_linkedin_profile(profile_url))

    # index = 0
    for link in linkedin_urls:
        print(link)
        profile_data.append(scrape_linkedin_profile(link))
        # index = index + 1
        # if(index == 2):
        #     break
        
    driver.quit()

    # File path to save JSON data
    file_path = "data.json"

    # Writing list to JSON file
    with open(file_path, "w") as json_file:
        json.dump(profile_data, json_file)

    # df = pd.DataFrame([profile_data])
    # df.to_csv("linkedin_profile.csv", index=False)


    print("Profile data saved to data.json")

# cara run program scrapping
# source venv/bin/activate  
# python index.py  
