# Telegram
import asyncio
import telepot
import telepot.aio
from telepot.aio.loop import MessageLoop
from pprint import pprint
import requests
from telegram import ParseMode

# Web Scraping
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import *
from selenium.common import *
from selenium.webdriver.common.by import By
import time

# Data manipulation
import pandas as pd

# Setting up the telegram bot
# Inputting /start shows the starting message
async def handle(msg):
    global chat_id
    content_type, chat_type, chat_id = telepot.glance(msg)
    pprint(msg)
    username = msg['chat']['first_name']
    if content_type == 'text':
        if msg['text'] != '/start':
            text = msg['text']
            text = text.strip()
            await getMeaning(text.lower())
        else:
            # /start
            message = """ Welcome, {0} :D\nPlease type in the product you would like to search for and i'll give you the first 5 options from both Lazada and Shopee, as well as the cheapest options from Shopee and Lazada 😊""".format(username)
            await bot.sendMessage(chat_id, message)

# Inputting anyting else rather than /start inputs it to the Lazada and Shopee search bars and outputs the given results
async def getMeaning(msg):
    
    # Web Scraping
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('disable-infobars')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-software-rasterizer')
    chrome_options.add_argument('window-size=1920,1080')
    
    # Create a browser using Chrome Web Driver
    browser = webdriver.Chrome(ChromeDriverManager().install(), options=chrome_options)

    # Assign search keyword
    search_item = msg

    # Assign Lazada website for scraping
    laz_url = 'https://www.lazada.com.ph'
    browser.get(laz_url)

    # Find the search bar through WebElement and type in search item
    laz_search_bar = browser.find_element(by = By.ID, value = "q")
    laz_search_bar.send_keys(search_item)

    # Find the search button through WebElement and click
    laz_search_button = browser.find_element(by = By.CLASS_NAME, value = "search-box__button--1oH7")
    browser.execute_script("arguments[0].click();", laz_search_button)

    laz_items = browser.find_elements(By.XPATH, '//div[contains(@class, "Bm3ON")]')

    # Initialize
    laz_names_list = []
    laz_prices_list = []
    laz_links_list = []

    # Scrape for names, prices, and links
    for item in laz_items:
        name = item.find_element(by = By.CLASS_NAME, value = "RfADt")
        laz_names_list.append(name.text)
        price = item.find_element(by = By.CLASS_NAME, value = "ooOxS")
        laz_prices_list.append(price.text)
        link = item.find_element(by = By.XPATH, value=' .//a[@age="0"]').get_attribute('href')
        laz_links_list.append(link)
    
    # Initialize laz_df
    laz_df = pd.DataFrame()
    laz_df["Titles"] = laz_names_list
    laz_df["Prices"] = laz_prices_list
    laz_df["Links"] = laz_links_list

    # Assign Shopee website for scraping
    shp_url = 'https://www.shopee.ph/'
    browser.get(shp_url)

    # Scrape for search bar, search button, and close button
    shp_search_bar = browser.find_element(by = By.CLASS_NAME, value= "shopee-searchbar-input__input")
    shp_search_button = browser.find_element(by = By.XPATH, value = "//button[contains(@class, 'btn btn-solid-primary btn--s btn--inline shopee-searchbar__search-button')]")
    shp_close_btn = browser.execute_script('return document.querySelector("#main shopee-banner-popup-stateful").shadowRoot.querySelector("div.home-popup__close-area div.shopee-popup__close-btn")')

    # Error handling
    try:
        shp_close_btn.click()
    except: 
        shp_search_bar.send_keys(search_item)
        shp_search_button.click()
    else:
        shp_search_bar.send_keys(search_item)
        shp_search_button.click()

    browser.implicitly_wait(10)

    # Look for preferred sellers
    shp_checkboxes = browser.find_elements(by = By.XPATH, value = "//span[contains(@class, 'shopee-checkbox__label')]")
    for i in shp_checkboxes:
        if i.text == "Preferred Sellers":
            i.click()

    # Check length of list of preferred items
    shp_preferred = browser.find_elements(by = By.XPATH, value = "//div[contains(@class, 'aLgMTQ')]") 

    # Initialize
    shp_names_list = []
    shp_prices_list = []
    shp_links_list = []

    # Scroll
    while True:
        last_height = browser.execute_script("return document.body.scrollHeight")
        browser.execute_script("window.scrollTo(0, window.scrollY + 1080)") #size of the Y-axis of the window
        time.sleep(1)
        new_height = browser.execute_script("return document.body.scrollHeight")

        if new_height == last_height:
            break
        else:
            last_height = new_height
            continue

    # Scrape for names, prices, and links
    shp_names = browser.find_elements(by = By.XPATH, value = "//div[contains(@class, 'ie3A+n bM+7UW Cve6sh')]")
    shp_prices = browser.find_elements(by = By.XPATH, value = "//div/div[2]/div[2]/div/span[2]")
    shp_links = browser.find_elements(by = By.XPATH, value = "//a[contains(@data-sqe, 'link')]")

    # Append text, href
    for i in range(len(shp_names)):
        shp_names_list.append(shp_names[i].text)
        shp_prices_list.append(shp_prices[i].text)
        shp_links_list.append(shp_links[i].get_attribute("href"))

    # Initialize shp_df
    shp_df = pd.DataFrame()
    shp_df["Titles"] = shp_names_list
    shp_df["Prices"] = shp_prices_list
    shp_df["Links"] = shp_links_list

    # Turning off truncating display option
    pd.set_option('display.max_colwidth', None)

    # Remove the Peso sign
    laz_df['Prices']=laz_df['Prices'].str[1:]

    # Merge the two dataframes
    all_df = pd.concat([laz_df, shp_df])

    # Remove comma from Prices, convert to int, and sort by ascending order according to Price
    all_df['Prices'] = all_df['Prices'].str.replace(',','')
    all_df['Prices'] = pd.to_numeric(all_df['Prices'])
    all_df = all_df.sort_values(by=['Prices'])

    # Converting Prices to string and adding a ₱ sign
    all_df['Prices']= all_df['Prices'].map(str)
    all_df['Prices'] = '₱' + all_df['Prices'].astype(str)

    # Reindexing the dataframe
    all_df = all_df.reset_index()
    all_df.drop(columns = "index")
    
    # Bot displays the first 5 results from Lazada
    await bot.sendMessage(chat_id, 
    '*First 5 options from Lazada:*\n\n'+
'1) ['+laz_df['Titles'][0]+']'+'('+laz_df['Links'][0]+')'+'\n'+'₱'+laz_df['Prices'][0]+'\n---------------\n'+
                          
'2) ['+laz_df['Titles'][1]+']'+'('+laz_df['Links'][1]+')'+'\n'+'₱'+laz_df['Prices'][1]+'\n---------------\n'+
              
'3) ['+laz_df['Titles'][2]+']'+'('+laz_df['Links'][2]+')'+'\n'+'₱'+laz_df['Prices'][2]+'\n---------------\n'+
                          
'4) ['+laz_df['Titles'][3]+']'+'('+laz_df['Links'][3]+')'+'\n'+'₱'+laz_df['Prices'][3]+'\n---------------\n'+
                          
'5) ['+laz_df['Titles'][4]+']'+'('+laz_df['Links'][4]+')'+'\n'+'₱'+laz_df['Prices'][4],parse_mode='Markdown')
    
    # Bot displays the first 5 results from Shopee
    await bot.sendMessage(chat_id, 
    '*First 5 options from Shopee:*\n\n'+
'1) ['+shp_df['Titles'][0]+']'+'('+shp_df['Links'][0]+')'+'\n'+'₱'+shp_df['Prices'][0]+'\n---------------\n'+
                          
'2) ['+shp_df['Titles'][1]+']'+'('+shp_df['Links'][1]+')'+'\n'+'₱'+shp_df['Prices'][1]+'\n---------------\n'+
              
'3) ['+shp_df['Titles'][2]+']'+'('+shp_df['Links'][2]+')'+'\n'+'₱'+shp_df['Prices'][2]+'\n---------------\n'+
                          
'4) ['+shp_df['Titles'][3]+']'+'('+shp_df['Links'][3]+')'+'\n'+'₱'+shp_df['Prices'][3]+'\n---------------\n'+
                          
'5) ['+shp_df['Titles'][4]+']'+'('+shp_df['Links'][4]+')'+'\n'+'₱'+shp_df['Prices'][4],parse_mode='Markdown')
    
    # Bot displays the 5 cheapest options from Lazada and Shopee
    await bot.sendMessage(chat_id, 
'*Top 5 cheapest options from both Lazada and Shopee:*\n\n'+
'1) ['+all_df['Titles'][0]+']'+'('+all_df['Links'][0]+')'+'\n'+all_df['Prices'][0]+'\n---------------\n'+
                          
'2) ['+all_df['Titles'][1]+']'+'('+all_df['Links'][1]+')'+'\n'+all_df['Prices'][1]+'\n---------------\n'+
              
'3) ['+all_df['Titles'][2]+']'+'('+all_df['Links'][2]+')'+'\n'+all_df['Prices'][2]+'\n---------------\n'+
                          
'4) ['+all_df['Titles'][3]+']'+'('+all_df['Links'][3]+')'+'\n'+all_df['Prices'][3]+'\n---------------\n'+
                          
'5) ['+all_df['Titles'][4]+']'+'('+all_df['Links'][4]+')'+'\n'+all_df['Prices'][4],parse_mode='Markdown')
                       

# Program startup
# Inputting the token obtained from @BotFather
bot = telepot.aio.Bot('5559162390:AAGZM54JbkrmvGhZUMTlBF7L-WVTEMAtpeI')
loop = asyncio.get_event_loop()
loop.create_task(MessageLoop(bot, handle).run_forever())
print('Listening...')

# Keep the program running
loop.run_forever()