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
import time
import subprocess
import re
import os
import posixpath
import yadisk

# Настройка Яндекс Диска
y = yadisk.YaDisk(token="**********") #Указать токен Яндекс Диска
to_dir = "/VideoParsing" # Указать путь к папке на Яндекс.Диске
from_dir = "C:/Video" # Указать локальный путь для сохранения видео

# Проверка существования папки на Яндекс Диске
if not y.exists(to_dir):
    y.mkdir(to_dir)
    print(f'Папка "{to_dir}" успешно создана на Яндекс.Диске')
else:
    print(f'Папка "{to_dir}" уже существует на Яндекс.Диске')

# Проверка используется ли сетевой порт для heartrate
def is_port_in_use(port):
    try:
        result = subprocess.run(['netstat', '-an'], stdout=subprocess.PIPE)
        output = result.stdout.decode('utf-8', errors='ignore')  # Используем 'ignore' для игнорирования ошибок декодирования
    except UnicodeDecodeError:
        return False  # В случае ошибки декодирования, предположим, что порт не используется

    regex = re.compile(r'.*:' + str(port) + r'\s')
    return any(regex.match(line) for line in output.splitlines())

# Запуск отслеживания выполнения кода, если порт свободен
if not is_port_in_use(9999):
    heartrate.trace(browser=True, port=9999)
else:
    print("Порт 9999 уже используется.")

# Исходные данные для сайта
url = 'https://e.muiv.ru/local/webinars/view.php' # Указать ссылку к сайту с роликами
username = '**********' # Указать логин
password = '**********' # Указать пароль

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

#  Скачивание видео по указанному URL и сохранение в локальном файле
def download_video(video_url, local_filename, cookies):
    if not os.path.exists(local_filename):  # Проверка, существует ли уже файл
        with requests.get(video_url, cookies=cookies, stream=True) as r:  # Отправка запроса на скачивание видео
            r.raise_for_status()  # Проверка на ошибки запроса
            total_size_in_bytes = int(r.headers.get('content-length', 0))  # Получение размера файла
            chunk_size = 1024 * 1024  # Установка размера части файла для скачивания
            progress_bar = tqdm(total=total_size_in_bytes, unit='iB', unit_scale=True)  # Инициализация прогресс-бара

            start_time = time.time()  # Запись времени начала скачивания
            with open(local_filename, 'wb') as file:  # Открытие файла для записи
                for data in r.iter_content(chunk_size):  # Чтение файла по частям
                    progress_bar.update(len(data))  # Обновление прогресс-бара
                    file.write(data)  # Запись данных в файл
            progress_bar.close()  # Закрытие прогресс-бара

            elapsed_time = time.time() - start_time  # Расчет времени скачивания и проверка на размер файла
            print(f"Download completed in {elapsed_time:.2f} seconds.")

            if total_size_in_bytes != 0 and progress_bar.n != total_size_in_bytes:
                print(
                    "ERROR: something went wrong during download")

# Изменение расширения ролика для скачивания
def change_extension(from_dir, file, new_ext):
    base = os.path.splitext(file)[0]
    new_file = base + new_ext
    os.rename(os.path.join(from_dir, file), os.path.join(from_dir, new_file))
    return new_file

# Загрузка видео на Яндекс Диск
def upload_to_yandex_disk(y, from_dir, file, to_dir):
    new_file = change_extension(from_dir, file, '.file')
    file_path = posixpath.join(to_dir, new_file)
    in_path = os.path.join(from_dir, new_file)
    try:
        y.upload(in_path, file_path)
    except yadisk.exceptions.PathExistsError as e:
        print(e)

# Проверка на наличие файла на Яндекс Диске
def is_file_on_yandex_disk(y, dir, filename):
    file_path = posixpath.join(dir, filename)
    return y.exists(file_path)

# Переход на сайт и ввод пароля и логина для получения ссылок
try:
    driver.get(url)  # Открытие указанного URL в браузере через WebDriver
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "username")))  # Ожидание появления поля ввода имени пользователя на странице в течение 10 секунд
    username_field = driver.find_element(By.ID, "username")  # Нахождение поля ввода имени пользователя
    username_field.send_keys(username)  # Ввод имени пользователя в найденное поле
    password_field = driver.find_element(By.ID, "password")  # Нахождение поля ввода пароля
    password_field.send_keys(password)  # Ввод пароля в найденное поле
    password_field.send_keys(Keys.RETURN)  # Имитация нажатия клавиши Enter для отправки формы

    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "topic_link")))  # Ожидание появления элементов с классом "topic_link" на странице

    selenium_cookies = {c['name']: c['value'] for c in driver.get_cookies()}  # Сохранение cookies из браузера в переменную
    soup = BeautifulSoup(driver.page_source, 'html.parser')  # Использование BeautifulSoup для парсинга исходного кода страницы
    video_links = soup.find_all('a', class_='topic_link', href=True)  # Поиск всех ссылок с классом "topic_link"

    video_count = 1
    for link in video_links:  # Цикл по всем найденным ссылкам
        video_title = clean_filename(link.get_text().strip())  # Очистка и форматирование названия видео
        local_filename_mp4 = os.path.join(save_path, f"{video_count}.{video_title}.mp4")  # Формирование пути для сохранения видео

        # Проверка на существование файла с расширением .file на Яндекс Диске
        file_exists_on_yandex = is_file_on_yandex_disk(y, to_dir, f"{video_count}.{video_title}.file")

        # Пропуск если видео существует на Яндекс Диске
        if file_exists_on_yandex:
            print(f"Видео {video_count} уже существует как .file на Яндекс Диске, пропускаем загрузку.")
            video_count += 1
            continue

        video_link_url = link['href']  # Получение URL видео
        if video_link_url.startswith("https://e.muiv.ru/play_video/index.html?f_name="):
            driver.get(video_link_url)  # Переход по ссылке видео
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, 'video')))  # Ожидание появления элемента video на странице

            video_url = driver.execute_script("return document.querySelector('video').src;")  # Получение прямой ссылки на видео

            # Скачивание видео, если оно еще не скачано
            if not os.path.exists(local_filename_mp4):
                download_video(video_url, local_filename_mp4, selenium_cookies)

            # Загрузка видео на Яндекс Диск
            upload_to_yandex_disk(y, save_path, f"{video_count}.{video_title}.mp4", to_dir)
            print(f"Видео {video_count} загружено на Яндекс Диск")

        video_count += 1

except Exception as e:
    print(f"Произошла ошибка: {e}")

finally:
    driver.quit()  # Закрытие браузера после завершения работы