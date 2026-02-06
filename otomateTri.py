from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import time, atexit
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def get_driver():
    options = webdriver.ChromeOptions()
    # attach to the already-running Chrome
    options.debugger_address = "127.0.0.1:9222"
    # do NOT add a user-data-dir here — Chrome is already started with it.
    driver = webdriver.Chrome(options=options)  # path to chromedriver in PATH
    return driver

driver = None
try:
    driver = get_driver()
    print("Attached to existing Chrome. Title:", driver.title)
    # Example: navigate a new tab (keeps session)
    driver.execute_script("window.open('https://www.blibli.com/digital/p/paket-data', '_blank');")
    time.sleep(5)
    # get parent container
    parent = driver.find_element(By.ID, "msisdnInput")

    # get child input inside parent
    child_input = parent.find_element(By.CSS_SELECTOR, "input.blu-text-field")

    # scroll the input itself, not the parent
    # driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", child_input)


    # type into it
    # find and click the clear button
    # try:
    clear_btn = parent.find_element(By.CLASS_NAME, "blu-field__clearable-btn")
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", clear_btn)
    time.sleep(5)

    # driver.execute_script("arguments[0].click();", clear_btn)
    clear_btn.click()
    # except:
    #     pass
    # clear_btn = parent.find_element(By.CLASS_NAME, "blu-field__clearable-btn")
    # clear_btn.click()

    child_input.send_keys("0895382511441")
    time.sleep(5)

    card = driver.find_element(
        By.XPATH,
        "//div[contains(@class,'select-product')][.//p[@class='form__product-content__name' and normalize-space(text())='H3RO 85 diamonds MLBB + 5GB']]"
    )
    print(card)
    # card.click()
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", card)
    driver.execute_script("arguments[0].click();", card)

    payButton = driver.find_element(By.ID, "btn-paynow")
    payButton.click()



    # do your automation...
except Exception as e:
    print("Error (driver still alive):", e)
    # IMPORTANT: don't call driver.quit() here if you want Chrome to remain open.
finally:
    # optional: keep driver object around or just exit without quitting
    print("Script exiting. Browser process stays open because we didn't quit it.")
