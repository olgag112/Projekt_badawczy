# pip install selenium webdriver-manager pandas
import pandas as pd
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


def scrape_gi_data():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # Realistic user-agent so the site doesn't block headless bots
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options
    )

    url = (
        "https://glycemicindex.com/gi-search/"
        "?food_name=&product_category=&country=&gi=55&gi_filter=lte"
        "&serving_size_(g)=&serving_size_(g)_filter="
        "&carbs_per_serve_(g)=&carbs_per_serve_(g)_filter="
        "&gl=10&gl_filter=lte"
    )

    all_data = []

    try:
        driver.get(url)
        print("Połączono ze stroną. Czekam na załadowanie danych...")
        time.sleep(5)  # Give JS time to render

        wait = WebDriverWait(driver, 20)

        try:
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
            print("Tabela znaleziona.")
        except TimeoutException:
            print("BŁĄD: Brak tabeli po 20s. Zrzut strony zapisany do debug.html")
            with open("debug.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            return

        # --- DEBUG: print all table-like selectors found ---
        tables = driver.find_elements(By.TAG_NAME, "table")
        print(f"Liczba tabel na stronie: {len(tables)}")
        for i, t in enumerate(tables):
            print(f"  Tabela {i}: class='{t.get_attribute('class')}'")

        page_num = 1
        while True:
            # Try broad selector first, fall back to any tbody tr
            rows = driver.find_elements(By.CSS_SELECTOR, ".gi-search-results__table tbody tr")
            if not rows:
                print("Próba alternatywnego selektora: 'table tbody tr'")
                rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")

            if not rows:
                print("Brak wierszy danych na tej stronie.")
                # Save HTML for inspection
                with open(f"debug_page_{page_num}.html", "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                print(f"Zapisano debug_page_{page_num}.html — sprawdź strukturę HTML.")
                break

            print(f"Strona {page_num}: znaleziono {len(rows)} wierszy.")
            for row in rows:
                cols = row.find_elements(By.TAG_NAME, "td")
                if len(cols) >= 6:
                    all_data.append({
                        "Food_Name":        cols[0].text.strip(),
                        "GI":               cols[1].text.strip(),
                        "GL":               cols[2].text.strip(),
                        "Serving_Size":     cols[3].text.strip(),
                        "Carbs_per_Serve":  cols[4].text.strip(),
                        "Category":         cols[5].text.strip(),
                    })

            # Pagination
            try:
                next_button = driver.find_element(By.PARTIAL_LINK_TEXT, "Next")
                classes = next_button.get_attribute("class") or ""
                if "disabled" in classes or not next_button.is_enabled():
                    print("Ostatnia strona osiągnięta.")
                    break
                driver.execute_script("arguments[0].click();", next_button)
                time.sleep(3)
                page_num += 1
                print(f"Przejście do strony {page_num}. Łącznie rekordów: {len(all_data)}")
            except Exception:
                print("Brak przycisku 'Next' — koniec paginacji.")
                break

    finally:
        driver.quit()

    # --- Safe DataFrame handling ---
    if not all_data:
        print("Nie zebrano żadnych danych. Sprawdź pliki debug_page_*.html.")
        return

    df = pd.DataFrame(all_data)
    print(f"\nKolumny w DataFrame: {df.columns.tolist()}")
    print(df.head())

    df.replace('', pd.NA, inplace=True)
    df.dropna(subset=['GI'], inplace=True)

    # Convert numeric columns
    for col in ['GI', 'GL', 'Serving_Size', 'Carbs_per_Serve']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    df.to_csv("gi_database_ml.csv", index=False, encoding="utf-8")
    print(f"\nSukces! Zapisano {len(df)} produktów do gi_database_ml.csv")


if __name__ == "__main__":
    scrape_gi_data()