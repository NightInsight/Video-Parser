# Импорт библиотек
from tqdm import tqdm
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import heartrate
import requests
import subprocess
import time
import re
import os

# Проверка используется ли сетевой порт для heartrate
# def is_port_in_use(port):
#     try:
#         result = subprocess.run(['netstat', '-an'], stdout=subprocess.PIPE)
#         output = result.stdout.decode('utf-8', errors='ignore')
#     except UnicodeDecodeError:
#         return False
#
#     regex = re.compile(r'.*:' + str(port) + r'\s')
#     return any(regex.match(line) for line in output.splitlines())

# # Запуск отслеживания выполнения кода, если порт свободен
# if not is_port_in_use(9999):
#     heartrate.trace(browser=True, port=9999)
# else:
#     print("Порт 9999 уже используется.")

# Исходные данные для сайта
url = 'https://e.muiv.ru/local/webinars/view.php'  # Указать ссылку к сайту с роликами
username = '**********'  # Указать логин
password = '**********'  # Указать пароль

# Инициализация и настройка драйвера браузера Chrome
chrome_options = Options()
chrome_options.add_argument("--headless")
driver = webdriver.Chrome(options=chrome_options)
driver.implicitly_wait(10)

# Указание пути для сохранения роликов
save_path = 'C:/Video'
os.makedirs(save_path, exist_ok=True)

# Очистка наименования файла от недопустимых символов и обрезания его до 50 символов
def clean_filename(filename):
    filename = re.sub(r'[\\/*?:"<>|]', "", filename)
    return filename[:50]

# Скачивание видео по указанному URL и сохранение в локальном файле
def download_video(video_url, local_filename, cookies):
    if not os.path.exists(local_filename):
        with requests.get(video_url, cookies=cookies, stream=True) as r:
            r.raise_for_status()
            total_size_in_bytes = int(r.headers.get('content-length', 0))
            chunk_size = 1024 * 1024
            progress_bar = tqdm(total=total_size_in_bytes, unit='iB', unit_scale=True)

            start_time = time.time()
            with open(local_filename, 'wb') as file:
                for data in r.iter_content(chunk_size):
                    progress_bar.update(len(data))
                    file.write(data)
            progress_bar.close()

            elapsed_time = time.time() - start_time
            print(f"Download completed in {elapsed_time:.2f} seconds.")

            if total_size_in_bytes != 0 and progress_bar.n != total_size_in_bytes:
                print("ERROR: something went wrong during download")

# Переход на сайт и ввод пароля и логина для получения ссылок
try:
    driver.get(url) # Открытие указанного URL в браузере через WebDriver
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "username")))
    username_field = driver.find_element(By.ID, "username")
    username_field.send_keys(username)
    password_field = driver.find_element(By.ID, "password") 
    password_field.send_keys(password)
    password_field.send_keys(Keys.RETURN)

    # Время ожидания
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "topic_link"))) 

    selenium_cookies = {c['name']: c['value'] for c in driver.get_cookies()} 
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    video_links = soup.find_all('a', class_='topic_link', href=True) 

    video_count = 1
    for link in video_links: # Цикл по всем найденным ссылкам
        video_title = clean_filename(link.get_text().strip()) 
        local_filename_mp4 = os.path.join(save_path, f"{video_count}.{video_title}.mp4") 

        # Проверка, существует ли файл видео уже в папке загрузки
        if os.path.exists(local_filename_mp4):
            print(f"Видео {video_count} уже скачано, пропускаем.")
            video_count += 1
            continue

        video_link_url = link['href'] # Получение URL видео
        if video_link_url.startswith("https://e.muiv.ru/play_video/index.html?f_name="):
            driver.get(video_link_url) 
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, 'video'))) 
            video_url = driver.execute_script("return document.querySelector('video').src;")

            download_video(video_url, local_filename_mp4, selenium_cookies) # Скачивание видео
            print(f"Видео {video_count} скачано и сохранено локально")

        video_count += 1

except Exception as e:
    print(f"Произошла ошибка: {e}")

finally:
    driver.quit()  # Закрытие браузера после завершения работы
