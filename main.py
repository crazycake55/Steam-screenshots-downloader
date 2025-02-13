import os
import time
import requests
import threading
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from webdriver_manager.chrome import ChromeDriverManager

STEAM_BASE_URL = "https://steamcommunity.com/id/"
SCROLL_PAUSE_TIME = 4

def update_status(message):
    status_label.config(text=message)
    root.update_idletasks()

def get_chrome_driver():
    driver_path = ChromeDriverManager().install()
    return Service(driver_path)

def get_full_page_source(steam_url):
    update_status("Connecting to Steam...")
    service = get_chrome_driver()
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(service=service, options=options)
    try:
        update_status("Loading page...")
        driver.get(steam_url)
        last_height = driver.execute_script("return document.body.scrollHeight")
        while True:
            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.END)
            time.sleep(SCROLL_PAUSE_TIME)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

        update_status("Page loaded. Analyzing...")
        return driver.page_source
    finally:
        driver.quit()

def get_games_from_page(page_source):
    soup = BeautifulSoup(page_source, 'html.parser')
    games = {}
    filter_section = soup.find("div", id="sharedfiles_filterselect_app_filterable")
    if filter_section:
        options = filter_section.find_all("div", class_="option ellipsis")
        for option in options:
            appid = option.get("onclick")
            if appid:
                appid = appid.split("'appid': '")[1].split("'")[0]
                game_name = option.text.strip()
                games[game_name] = appid
    return games

def get_screenshot_page_links(page_source):
    soup = BeautifulSoup(page_source, 'html.parser')
    return [a_tag.get("href") for a_tag in soup.find_all("a", class_="profile_media_item") if a_tag.get("href")]

def get_image_from_screenshot_page(page_url):
    response = requests.get(page_url)
    if response.status_code != 200:
        return None
    soup = BeautifulSoup(response.text, 'html.parser')
    img_tag = soup.find("img", id="ActualMedia")
    return img_tag["src"] if img_tag and "src" in img_tag.attrs else None

def download_images(image_links, save_folder, steam_id, game_name):
    formatted_name = game_name.replace(",", " ").replace(":", " ").replace("'", " ").replace('"', " ").replace(" ", "_")
    if len(formatted_name) > 10:
        words = game_name.split()
        formatted_name = "".join([word[0].upper() for word in words])
    if not os.path.exists(save_folder):
        os.makedirs(save_folder)

    total_images = len(image_links)
    downloaded_images = 0

    for idx, link in enumerate(image_links):
        response = requests.get(link, stream=True)
        if response.status_code == 200:
            file_name = os.path.join(save_folder, f"screenshot_{steam_id}_{formatted_name}_{idx + 1}.jpg")
            with open(file_name, "wb") as file:
                for chunk in response.iter_content(1024):
                    file.write(chunk)

            downloaded_images += 1
            status_label.config(text=f"Downloading screenshots... {downloaded_images}/{total_images}")
            root.update()

    if downloaded_images == total_images:
        update_status(f"Downloaded {downloaded_images} images.")
    else:
        update_status("No images found on the screenshot pages.")

games = {}

def clear_game_list(*args):
    game_selector.set('')
    game_selector['values'] = []


def fetch_games():
    global games
    steam_id = steam_id_entry.get().strip()
    if not steam_id:
        messagebox.showerror("Error", "Please enter a Steam ID.")
        return
    update_status("Fetching games...")
    progress_bar.start()
    def task():
        try:
            base_url = f"{STEAM_BASE_URL}{steam_id}/screenshots/"
            page_source = get_full_page_source(base_url)
            games.update(get_games_from_page(page_source))
            if games:
                game_selector["values"] = list(games.keys())
                update_status("Games fetched successfully.")
            else:
                update_status("No games found or profile is private.")
        except Exception as e:
            status_label.config(text=f"Error: {str(e)}")
        finally:
            progress_bar.stop()
    threading.Thread(target=task, daemon=True).start()

def start_download():
    global games
    steam_id = steam_id_entry.get().strip()
    selected_game = game_selector.get()
    save_folder = filedialog.askdirectory(title="Select Save Folder")
    if not steam_id or not selected_game or not save_folder:
        messagebox.showerror("Error", "Please fill in all fields.")
        return
    update_status("Downloading screenshots...")
    progress_bar.start()
    def task():
        try:
            base_url = f"{STEAM_BASE_URL}{steam_id}/screenshots/"
            app_id = games[selected_game]
            full_url = f"{base_url}?appid={app_id}"
            page_source = get_full_page_source(full_url)
            page_links = get_screenshot_page_links(page_source)
            if not page_links:
                update_status("No screenshots found.")
                return
            image_links = [get_image_from_screenshot_page(link) for link in page_links if link]
            image_links = [img for img in image_links if img]
            if image_links:
                download_images(image_links, save_folder, steam_id, selected_game)
                update_status(f"Downloaded {len(image_links)} images.")
            else:
                update_status("No images found on the screenshot pages.")
        except Exception as e:
            status_label.config(text=f"Error: {str(e)}")
        finally:
            progress_bar.stop()
    threading.Thread(target=task, daemon=True).start()

root = tk.Tk()
root.title("Steam Screenshot Downloader")
frame = tk.Frame(root, padx=10, pady=10)
frame.pack(fill=tk.BOTH, expand=True)
tk.Label(frame, text="Steam ID:").grid(row=0, column=0, sticky=tk.W)
steam_id_entry = tk.Entry(frame, width=30)
steam_id_entry.grid(row=0, column=1, sticky=tk.W)
steam_id_entry.bind("<KeyRelease>", clear_game_list)
fetch_games_button = tk.Button(frame, text="Fetch Games", command=fetch_games)
fetch_games_button.grid(row=0, column=2, sticky=tk.W)
tk.Label(frame, text="Select Game:").grid(row=1, column=0, sticky=tk.W)
game_selector = ttk.Combobox(frame, state="readonly", width=30)
game_selector.grid(row=1, column=1, sticky=tk.W)
download_button = tk.Button(frame, text="Download Screenshots", command=start_download)
download_button.grid(row=2, column=0, columnspan=3, pady=10)
progress_bar = ttk.Progressbar(frame, mode="indeterminate", length=300)
progress_bar.grid(row=3, column=0, columnspan=3, pady=5)
status_label = tk.Label(frame, text="", fg="blue")
status_label.grid(row=4, column=0, columnspan=3, pady=5)
root.mainloop()
