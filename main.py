import os
import time
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog, messagebox

STEAM_BASE_URL = "https://steamcommunity.com/id/"
SCROLL_PAUSE_TIME = 4


def get_full_page_source(steam_url):
    driver_path = "C:/steamScreenshotsGet/chromedriver.exe"
    service = Service(driver_path)
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(service=service, options=options)
    try:
        driver.get(steam_url)
        last_height = driver.execute_script("return document.body.scrollHeight")
        while True:
            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.END)
            time.sleep(SCROLL_PAUSE_TIME)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
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
    page_links = []
    for a_tag in soup.find_all("a", class_="profile_media_item"):
        href = a_tag.get("href")
        if href:
            page_links.append(href)
    return page_links


def get_image_from_screenshot_page(page_url):
    response = requests.get(page_url)
    if response.status_code != 200:
        return None
    soup = BeautifulSoup(response.text, 'html.parser')
    img_tag = soup.find("img", id="ActualMedia")
    if img_tag and "src" in img_tag.attrs:
        return img_tag["src"]
    return None


def download_images(image_links, save_folder, steam_id, game_name):
    formatted_name = game_name.replace(",", " ").replace(":", " ").replace("'", " ").replace('"', " ").replace(" ", "_")

    if len(formatted_name) > 10:
        words = game_name.split()
        formatted_name = "".join([word[0].upper() for word in words])

    if not os.path.exists(save_folder):
        os.makedirs(save_folder)
    for idx, link in enumerate(image_links):
        response = requests.get(link, stream=True)
        if response.status_code == 200:
            file_name = os.path.join(save_folder, f"screenshot_{steam_id}_{formatted_name}_{idx + 1}.jpg")
            with open(file_name, "wb") as file:
                for chunk in response.iter_content(1024):
                    file.write(chunk)

games = {}
def fetch_games():
    global games
    steam_id = steam_id_entry.get().strip()
    if not steam_id:
        messagebox.showerror("Error", "Please enter a Steam ID.")
        return
    try:
        base_url = f"{STEAM_BASE_URL}{steam_id}/screenshots/"
        page_source = get_full_page_source(base_url)
        games = get_games_from_page(page_source)
        if games:
            game_selector["values"] = list(games.keys())
            messagebox.showinfo("Success", "Games fetched successfully.")
        else:
            messagebox.showwarning("Warning", "No games found or profile is private.")
    except Exception as e:
        messagebox.showerror("Error", str(e))


def start_download():
    global games
    steam_id = steam_id_entry.get().strip()
    selected_game = game_selector.get()
    save_folder = filedialog.askdirectory(title="Select Save Folder")
    if not steam_id or not selected_game or not save_folder:
        messagebox.showerror("Error", "Please fill in all fields.")
        return
    try:
        base_url = f"{STEAM_BASE_URL}{steam_id}/screenshots/"
        app_id = games[selected_game]
        full_url = f"{base_url}?appid={app_id}"
        page_source = get_full_page_source(full_url)
        page_links = get_screenshot_page_links(page_source)
        if not page_links:
            messagebox.showwarning("Warning", "No screenshots found.")
            return
        image_links = []
        for page_link in page_links:
            image_url = get_image_from_screenshot_page(page_link)
            if image_url:
                image_links.append(image_url)
        if image_links:
            download_images(image_links, save_folder, steam_id, selected_game)
            messagebox.showinfo("Success", f"Downloaded {len(image_links)} images to {save_folder}.")
        else:
            messagebox.showwarning("Warning", "No images found on the screenshot pages.")
    except Exception as e:
        messagebox.showerror("Error", str(e))


root = tk.Tk()
root.title("Steam Screenshot Downloader")

frame = tk.Frame(root, padx=10, pady=10)
frame.pack(fill=tk.BOTH, expand=True)

tk.Label(frame, text="Steam ID:").grid(row=0, column=0, sticky=tk.W)
steam_id_entry = tk.Entry(frame, width=30)
steam_id_entry.grid(row=0, column=1, sticky=tk.W)

fetch_games_button = tk.Button(frame, text="Fetch Games", command=fetch_games)
fetch_games_button.grid(row=0, column=2, sticky=tk.W)

tk.Label(frame, text="Select Game:").grid(row=1, column=0, sticky=tk.W)
game_selector = ttk.Combobox(frame, state="readonly", width=30)
game_selector.grid(row=1, column=1, sticky=tk.W)
download_button = tk.Button(frame, text="Download Screenshots", command=start_download)
download_button.grid(row=2, column=0, columnspan=3, pady=10)
root.mainloop()
