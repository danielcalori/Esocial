import os
import time
import requests
from datetime import datetime

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from twilio.rest import Client

def get_driver_uc():
    options = uc.ChromeOptions()
    
    # For production, use headless=True; for debugging, set to False.
    options.headless = True  
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--remote-debugging-port=9222")
    options.add_argument("--window-size=1920,1080")
    
    # Set a typical desktop user agent
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36")
    
    # Optionally, try commenting this out if it causes issues:
    # options.add_argument("--disable-blink-features=AutomationControlled")
    
    # Specify the path to Chromium (this should be correct for GitHub Actions)
    options.binary_location = "/usr/bin/chromium-browser"
    
    # Force undetected_chromedriver to use the ChromeDriver version that matches Chromium 132
    driver = uc.Chrome(options=options, version_main=132)
    return driver



def login_esocial(driver, cpf, senha):
    try:
        print("🔵 Accessing eSocial login page...")
        driver.get("https://login.esocial.gov.br/login.aspx")
        wait = WebDriverWait(driver, 40)  # Increased timeout
        # Use a more flexible locator:
        botao_gov = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'gov.br')]")))
        botao_gov.click()
        
        campo_cpf = wait.until(EC.presence_of_element_located((By.ID, "login-cpf")))
        campo_cpf.send_keys(cpf)
        
        botao_gov2 = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'continuar')]")))
        botao_gov2.click()
        
        campo_senha = driver.find_element(By.ID, "password")
        campo_senha.send_keys(senha)
        campo_senha.send_keys(Keys.RETURN)
        wait.until(EC.presence_of_element_located((By.XPATH, "//h1[contains(text(), 'Bem-vindo')]")))
        print("✅ Login successful!")
    except Exception as e:
        print("❌ Login error:", e)
        print("Page source snapshot:")
        print(driver.page_source[:2000])  # print first 2000 characters
        raise


def generate_salary_guide(driver, month):
    wait = WebDriverWait(driver, 20)
    folha_menu = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Folha de Pagamento')]")))
    folha_menu.click()
    opcao_mes = wait.until(EC.element_to_be_clickable((By.XPATH, f"//select[@id='mes']/option[@value='{month}']")))
    opcao_mes.click()
    close_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Encerrar Folha')]")))
    close_button.click()
    guide_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Emitir Guia de Pagamento')]")))
    guide_button.click()
    print("✅ Salary guide generated successfully!")

def capture_payment_code_and_download_pdf(driver):
    wait = WebDriverWait(driver, 20)
    codigo_elemento = wait.until(EC.presence_of_element_located((By.ID, "codigoGuia")))
    codigo_guia = codigo_elemento.text.strip()
    print(f"📌 Payment Code: {codigo_guia}")
    link_pdf = wait.until(EC.presence_of_element_located(
        (By.XPATH, "//a[contains(@href, '.pdf') and contains(text(), 'Baixar PDF')]")
    ))
    pdf_url = link_pdf.get_attribute("href")
    response = requests.get(pdf_url)
    if response.status_code == 200:
        pdf_path = f"guia_{datetime.now().strftime('%Y%m%d')}.pdf"
        with open(pdf_path, "wb") as f:
            f.write(response.content)
        print(f"📄 PDF saved: {pdf_path}")
        return codigo_guia, pdf_path
    else:
        print("❌ Failed to download PDF")
        return None, None

def send_sms_twilio(message):
    client = Client(os.environ["TWILIO_SID"], os.environ["TWILIO_TOKEN"])
    sent_message = client.messages.create(
        body=message,
        from_=os.environ["TWILIO_NUMBER"],
        to=os.environ["PHONE_NUMBER"]
    )
    print("📩 SMS sent successfully!")

def run_esocial_automation():
    driver = get_driver_uc()
    try:
        login_esocial(driver, os.environ["ESOCIAL_CPF"], os.environ["ESOCIAL_SENHA"])
        generate_salary_guide(driver, "02")  # For example, process February ("02")
        code, pdf_path = capture_payment_code_and_download_pdf(driver)
        if code and pdf_path:
            send_sms_twilio(f"✅ Salary guide ready! Code: {code} PDF: {pdf_path}")
    finally:
        driver.quit()
        print("🚀 Automation completed!")

if __name__ == "__main__":
    run_esocial_automation()
