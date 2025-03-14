import os
import io
import requests
import pdfplumber
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
import time
import re
import sqlite3 

# Extracting monetary settlement from text
def extract_settlement_value(text):
    match = re.search(r'\$\s?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', text) # Searching for values in format like $10,000.00 or $10000.00
    if match:
        return match.group(0)
    return "Not Found"

driver = webdriver.Chrome()

driver.get("https://programs.iowadnr.gov/documentsearch/Home/OTCSSearch")

time.sleep(2)

# Select "25" rows from the dropdown so we have 25 records on the page
# This will make it easier to extract the data from the table
limit_dropdown = Select(driver.find_element(By.XPATH, '//*[@id="Limit"]'))
limit_dropdown.select_by_value("25")  

time.sleep(2)

# Select "Enforcement Orders" from the dropdown this can be changed to other options as needed 
program_dropdown = Select(driver.find_element(By.XPATH, '//*[@id="Program"]'))
program_dropdown.select_by_value("DNR - Administrative Orders")

# Click the "Search Documents" button
search_button = driver.find_element(By.XPATH, '//*[@id="searchSubmit"]')
search_button.click()


time.sleep(3)

# Uncomment the below code to create a folder to save the PDFs
#pdf_folder = "pdfs"
#if not os.path.exists(pdf_folder):
    #os.makedirs(pdf_folder)


# Createing SQLite Database and Table
# Connect to SQLite database
conn = sqlite3.connect('scraped_data.db')
cursor = conn.cursor()

# Create a table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS scraped_information (
        id INTEGER PRIMARY KEY,
        Defendant TEXT,
        Plaintiff TEXT,
        Year INTEGER,
        Settlement TEXT,
        "Violation Type" TEXT,
        "Data Source Link" TEXT
    )
""")
conn.commit()

# Extracting records
print("\nExtracted Data with Settlement Info:")
print("=" * 80)

for i in range(2, 7):  #first 5 records
    try:
        facility_name_xpath = f'//*[@id="ResultsTable"]/tbody/tr[{i}]/td[6]'
        year_xpath = f'//*[@id="ResultsTable"]/tbody/tr[{i}]/td[3]'
        document_link_xpath = f'//*[@id="ResultsTable"]/tbody/tr[{i}]/td[1]/a'

        # Extracting data
        facility_name = driver.find_element(By.XPATH, facility_name_xpath).text
        year_full = driver.find_element(By.XPATH, year_xpath).text  # Full date format
        year = year_full.split("/")[-1]  # Extract the year from the date
        document_link = driver.find_element(By.XPATH, document_link_xpath).get_attribute("href")

        # Static values for Plaintiff and Violation Type
        plaintiff = "Iowa DoNR"
        violation_type = "Environmental"

        # Uncomment the below code to download the PDFs

        #pdf_name = f"{facility_name}_{year}.pdf"
        #pdf_path = os.path.join(pdf_folder, pdf_name)
        #response = requests.get(document_link)
        #with open(pdf_path, "wb") as pdf_file:
            #pdf_file.write(response.content)

        response = requests.get(document_link)
        pdf_bytes = io.BytesIO(response.content)

        # Here we will extract the Settlement information from the PDF
        settlement = "Not Found"
        with pdfplumber.open(pdf_bytes) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if "Settlement" in text or "Penalty" in text or "Monetary" in text or "fine" in text or "amount" in text:
                    settlement = extract_settlement_value(text)
                    if settlement != "Not Found":
                        break

        # Insert data into SQLite table we created earlier
        cursor.execute("""
            INSERT INTO scraped_information (Defendant, Plaintiff, Year, Settlement, "Violation Type", "Data Source Link")
            VALUES (?, ?, ?, ?, ?, ?)
        """, (facility_name, plaintiff, year, settlement, violation_type, document_link))
        conn.commit()

        # Printing extracted data to the console
        print(f"Defendant: {facility_name}")
        print(f"Plaintiff: {plaintiff}")
        print(f"Year: {year}")
        print(f"Settlement: {settlement}")
        print(f"Violation Type: {violation_type}")
        print(f"Data Source Link: {document_link}")
        print("-" * 80)

    except Exception as e:
        print(f"Error extracting row {i}: {e}")

conn.commit()
conn.close()
driver.quit()
