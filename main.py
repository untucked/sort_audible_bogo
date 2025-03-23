from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import sys
import pandas as pd
import time
import os
import re
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def test_profiles_in_chrome(chromedriver_path, options, audible_url):
    profiles_to_try = ["SeleniumScraper", "Default", "Profile 1", "Profile 2"] 
    for profile in profiles_to_try:
        options.add_argument(f"--profile-directory={profile}")
        service = Service(chromedriver_path)
        driver = webdriver.Chrome(service=service, options=options)
        driver.get(audible_url)
        time.sleep(5) 
        driver.save_screenshot(f"audible_screenshot_{profile}.png")
        print(f"Successfully loaded profile: {profile}")
        driver.quit()

    sys.exit()

audible_url = "https://www.audible.com/special-promo/2for1/cat?node=120291920011&pageSize=50&page=1"
# Get the user's local app data directory
username = os.getenv('USERNAME')
profile_path = r'C:\Users\%s\AppData\Local\Google\Chrome\User Data'%(username)
# Configure webdriver
chromedriver_path = os.path.join(
    r"C:\Users\%s\Documents\python\chromedriver-win64\chromedriver-win64\chromedriver.exe"%(username)
)
options = Options()
options.add_argument("--start-maximized")
options.add_argument(f"--user-data-dir={profile_path}") # This line is correct.
# Try with different profiles (adjust as needed)
test_profiles = True
if test_profiles:
    test_profiles_in_chrome(chromedriver_path, options, audible_url)

options.add_argument(f"--profile-directory={"Profile 1"}")
service = Service(chromedriver_path)
driver = webdriver.Chrome(service=service, options=options)

driver.get(audible_url)
# Explicit wait to confirm login and page load
wait = WebDriverWait(driver, 15)
try:
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "ul.bc-list.bc-list-nostyle")))
except Exception as e:
    print("Initial page load failed. Check your profile or login.")
    driver.quit()
    exit()
all_books = []
skip_count = 0
max_skips = 3
# Get total number of pages (with improved robustness)
try:
    pagination_elements = wait.until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'ul.pagingElements li'))
    )
    total_pages = int(pagination_elements[-2].text.strip())
except Exception as e:
    print(f"Could not determine total pages: {e}. Defaulting to 10.")
    total_pages = 10

print(f"Total pages found: {total_pages}")

for page in range(1, total_pages + 1):
    print(f"Scraping page {page}")
    if page>1:
        url = f"https://www.audible.com/special-promo/2for1/cat?node=120291920011&pageSize=50&page={page}"
        driver.get(url)
       # Wait explicitly for book elements to load
    try:
        books = wait.until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'li.bc-list-item.productListItem'))
        )
        time.sleep(2)
    except Exception as e:
        print(f"No books loaded on page {page}: {e}")
        break
    if not books:
        print(f'No books found on page {page}')
        break
    for book in books:
        try:
            title_elem = book.find_element(By.CSS_SELECTOR, "h3.bc-heading a")
            title = title_elem.text.strip()

            length_elem = book.find_elements(By.CSS_SELECTOR, 'li.runtimeLabel')
            length = length_elem[0].text.replace('Length:', '').strip() if length_elem else 'Unknown'
            rating_elem = book.find_elements(By.CSS_SELECTOR, 'li.ratingsLabel')
            num_ratings = '0' #default value.
            if rating_elem:
                rating_text = rating_elem[0].text.strip().replace('\n', ' ') #Replaced the newline with a space.
                match = re.search(r'\d{1,3}(,\d{3})*(?=\sratings?)', rating_text)
                if match:
                    num_ratings = match.group(0).replace(',','')
            all_books.append({
                "Title": title,
                "Length": length,
                "Number of Ratings": int(num_ratings)
            })
            skip_count = 0 #reset skip count.
        except Exception as e:
            print("Error processing book entry:", e)
            skip_count += 1
            if skip_count >= max_skips:
                print("Exceeded max skips. Ending scraping.")
                break
            continue

    if skip_count >= max_skips:
        print("Exceeded max skips. Ending scraping.")
        break
    # polite scraping, reduce chances of blocking
    time.sleep(2)
driver.quit()

# Convert to DataFrame and sort by number of ratings
if all_books:
    df = pd.DataFrame(all_books)
    df.sort_values(by="Number of Ratings", ascending=False, inplace=True)

    # Save to CSV
    df.to_csv("audible_books_ranked.csv", index=False)
    print("Data saved to audible_books_ranked.csv")
else:
    print("No data was scraped.")