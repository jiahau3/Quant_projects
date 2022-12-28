from bs4 import BeautifulSoup
from datetime import datetime
import json
import numpy as np
import os
import pandas as pd
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
# from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
# from tda import auth, client
import time

def get_keys(path):
    """
    This function will get dictionary of keys from a stored json file
    :param path: (str) directory path for the .json file with keys
    """
    with open(path) as f:
        return json.load(f)

def search_symbol(driver, ticker):
    """
    This function searches for a ticker symbol on TD Ameritrade website once
    user is logged in.
    :param driver: (Selenium webdriver) webdriver returned from start_bot()
    :param ticker: (str) ticker symbol to search
    """

    # Attempt the more expedient symbol lookup, rever to main search otherwise
    try:
        search = driver.find_element(By.XPATH, '//*[@id="symbol-lookup"]')
        search.click()
        search.clear()
    except:
        driver.switch_to.default_content()
        search = driver.find_element(By.NAME, "search")
        kind = 'search'
    else:
        kind = 'symbol'
    # Enter ticker symbol to search and click search button
    search.send_keys(ticker)
    if kind == 'symbol':
        driver.find_element(By.XPATH, '//*[@id="layout-full"]/div[1]/div/div[1]/div/a').click()
    elif kind == 'search':
        driver.find_element(By.ID ,"searchIcon").click()
    # Give extra time for webpage to load
    time.sleep(4)

def reduce_tabs(driver):
    """
    This function is used when an action opens the result on a new tab, in
    order to reduce the number of browser tabs back to 1, and switch to the
    intended tab.
    :param driver: (Selenium webdriver)
    """
    if len(driver.window_handles) > 1:
        driver.switch_to.window(driver.window_handles[0])
        driver.close()
        driver.switch_to.window(driver.window_handles[0])

def clean(x, show_errors=False):
    """
    This function is used to clean strings containing numeric data of the 
    common issues found in TD Ameritrade's website
    """
    #print("cleaning {} of type {}".format(x, type(x)))
    not_date = True
    multiple = 1
    if isinstance(x, str):
        check = re.split('/|-|, ', x)
        x = x.strip()
        x = x.replace(',','')

        if x.startswith('(') and x.endswith(')'):
            x = x.strip('(').strip(')')
            x = '-'+x

        if x.endswith('%'):
            x = x.replace('%','')
            multiple = 1/100
        elif x.endswith('x'):
            x = x.strip('x')
            if x == '--':
                x = np.NaN
            else:
                x = x

        if x.endswith('k') or x.endswith('K'):
            x = x.upper().replace('K','')
            multiple = 1000

        if x.startswith('$') or x.startswith('-$'):
            x = x.replace('$','')
        elif len(check) > 1 and check[-1].isdigit():
            not_date = False
            if x.startswith('(Unconfirmed)'):
                x = x.replace('(Unconfirmed) ','')
            x = pd.to_datetime(x, infer_datetime_format=True)

        if x == '--':
            x = np.NaN

        if not_date:
            try:
                x = float(x) * multiple
            except:
                if show_errors:
                    print(x) 
                x = np.NaN
    #print('returning {}'.format(x))
    return x   

def start_bot(keys):
    """
    Starts TD Ameritrade Scraping Bot. Takes input of dictionary containing 
    username and password which must have keys "user" and "pass" with the 
    values to be used. Returns webdriver object to be used for session.
    :param keys: (dict) dictionary with username ("user") and password ("pass")
    """
    driver = webdriver.Chrome()
    #driver.implicitly_wait(20)
    login_url = 'https://invest.ameritrade.com/grid/p/login'
    try:
        driver.get(login_url)
    except:
        raise ValueError('Caanot find Login button')
    else:
        assert "TD Ameritrade Login" in driver.title
        WebDriverWait(driver, 10).until(lambda x: x.find_element(By.CSS_SELECTOR, 'button.cafeLoginButton')).click()
        username = WebDriverWait(driver, 10).until(lambda x: x.find_element(By.ID, 'username0'))
        username.send_keys(keys["user"])
        password = WebDriverWait(driver, 10).until(lambda x: x.find_element(By.ID, "password1"))
        password.send_keys(keys["pass"])
        try:
            driver.find_element(By.CSS_SELECTOR, 'input#accept.accept.button').click()
        except:
            raise ValueError("Login fails.")
        else:
            try:
                WebDriverWait(driver, 10).until(lambda x: EC.text_to_be_present_in_element(x, 'Use desktop website'))
                time.sleep(3)
                button = WebDriverWait(driver, 10).until(lambda x: x.find_element(By.XPATH, value='//*[@id="app"]/div/div[2]/footer/div/ul/li[1]/button'))
                button.click()
                time.sleep(3)
                home_url = driver.current_url
                reduce_tabs(driver)
            except:
                return driver

    return driver

def scrape_summary(driver, ticker, search_first=True, return_full=False, internet_speed='fast'):
    """
    This function scrapes the "Summary" tab of a TD Ameritrade security
    lookup page
    :param driver: (Selenium webdriver) webdriver returned from start_bot()
    :param ticker: (str) ticker symbol to scrape
    :param search_first: (bool) allows for chain of scrapes to be done on one
                                security when set to False. Leave set to True
                                unless you are sure you are already on the
                                desired security, or the wrong data will scrape
    :param return_full: (bool) will return dataframe with extra column containing
                               feature descriptions for the rows.
    :param internet_speed: (str) set to 'slow' if bot is not working properly due
                                to slow page loading times.
    """
    # Search symbol first if flag is True:
    if search_first:
        search_symbol(driver, ticker)
        if internet_speed == 'slow':
            time.sleep(1)
    #tabs = get_tab_links()
    #driver.get(tabs['Summary'])

    if internet_speed == 'fast':
        sleep_time = 1
    elif internet_speed == 'slow':
        sleep_time = 2

    # Find main iframe
    driver.switch_to.default_content()
    iframes = WebDriverWait(driver, 10).until(lambda x: x.find_elements(By.TAG_NAME, "iframe"))
    driver.switch_to.frame(iframes[3])

    # Switch to Summary tab
    WebDriverWait(driver, 10).until(lambda x: EC.text_to_be_present_in_element(x, 'Summary'))
    WebDriverWait(driver, 10).until(lambda x: x.find_element(By.XPATH, '//*[@id="layout-full"]/nav/ul/li[1]/a')).click()
    
    # Wait for conditions to be met before making soup
    element = driver.find_element(By.XPATH, '//*[@id="stock-summarymodule"]/div/div/div[2]/div')
    WebDriverWait(driver, 10).until(lambda x: EC.visibility_of_element_located(element))
    # Add extra time for data to load
    time.sleep(sleep_time)
    
    # Make soup and find elements
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    dts = soup.find_all('dt')

    # Set flag which will be made false if no dividend is given
    dividend_given = True
    texts = []
    for dt in dts:
        try:
            texts.append(dt.get_text('|'))        
        except:
            print("error")
            continue

    dds = soup.find_all('dd')
    values = []
    for dd in dds:
        try:
            values.append(dd.get_text('|'))        
        except:
            print("error")
            continue

    fields = [x.split('|')[0] for x in texts]
    alt_info = [x.split('|')[1:] for x in texts]

    # Make dataframe and fix row names
    data_dict = dict(zip(fields,zip(alt_info,values)))
    temp = pd.DataFrame.from_dict(data_dict, orient='index')
    temp.loc['Volume', 1] = temp.loc['Volume', 0][0].strip()
    temp.rename(index={'Volume:':'Volume 10-day Avg',
                          'Volume':'Volume Past Day',
                          '10-day average volume:':'Volume',
                          'Score:':'New Constructs Score'
                        }, inplace=True)
    temp.loc['52-Wk Range', 1] = temp.loc['52-Wk Range', 0]
    price_feat = 'Closing Price'
    if price_feat not in temp.index:
        if 'Price' in temp.index:
            price_feat = 'Price'

    # Cleaning data
    if temp.loc["B/A Size",1] == '--': 
        temp = temp.append(pd.Series([[],
                                  np.NaN
                                 ],
                                 name="Bid Size"),
                      )
        temp = temp.append(pd.Series([[],
                                  np.NaN
                                 ],
                                 name="Ask Size"),
                      )
        temp = temp.append(pd.Series([[],
                                  np.NaN
                                 ],
                                 name="B/A Ratio"),
                      )
    else:
        temp = temp.append(pd.Series([[],
                                  float(temp.loc['B/A Size',1].split('x')[0])
                                 ],
                                 name="Bid Size"),
                      )
        temp = temp.append(pd.Series([[],
                                  float(temp.loc['B/A Size',1].split('x')[1])
                                 ],
                                 name="Ask Size"),
                      )
        temp = temp.append(pd.Series([[],
                                  float(temp.loc['B/A Size',1].split('x')[0])
                                            /float(temp.loc['B/A Size',1].split('x')[1])
                                 ],
                                 name="B/A Ratio"),
                    )  
    if temp.loc["Day's Range",1] == '--':
        temp = temp.append(pd.Series([[],
                                  np.NaN,
                                 ],
                                 name="Day Change $"
                                ),
                      )
        temp = temp.append(pd.Series([[],
                                  np.NaN
                                 ],
                                 name="Day Change %"
                                ),
                      )
        temp = temp.append(pd.Series([[],
                                 np.NaN
                                 ],
                                name="Day Low"),
                      )
        temp = temp.append(pd.Series([[],
                                 np.NaN
                                 ],
                                name="Day High"),
                      )
    else:
        temp = temp.append(pd.Series([[],float(temp.loc["Day's Change",1].split('|')[0].strip('|'))],
                                 name="Day Change $"
                                ),
                      )
        temp = temp.append(pd.Series([[],
                                  float(temp.loc["Day's Change",1].split('|')[2].strip('%)').strip('()'))/100
                                 ],
                                 name="Day Change %"
                                ),
                      )
        temp = temp.append(pd.Series([[],
                                 float(temp.loc["Day's Range",1].split('-')[0].strip('|').replace(',',''))
                                 ],
                                name="Day Low"),
                      )
        temp = temp.append(pd.Series([[],
                                 float(temp.loc["Day's Range",1].split('-')[1].strip('|').replace(',',''))
                                 ],
                                name="Day High"),
                      )
    if temp.loc["Annual Dividend/Yield",1] != 'No dividend':
        temp = temp.append(pd.Series([[],
                                 float(temp.loc["Annual Dividend/Yield",1].split('/')[0].strip('$'))
                                 ],
                                name="Annual Dividend $"))

        temp = temp.append(pd.Series([[],
                                 float(temp.loc["Annual Dividend/Yield",1].split('/')[1].strip('%'))/100
                                 ],
                                name="Annual Dividend %"))
    else:
        dividend_given = False
        temp = temp.append(pd.Series([[],
                                 np.NaN
                                 ],
                                name="Annual Dividend $"))
        temp = temp.append(pd.Series([[],
                                 np.NaN
                                 ],
                                name="Annual Dividend %"))
    temp.rename(columns={1:ticker}, inplace = True)
    drop = ["Day's Change", 
            "Day's Range",
            "Day's High",
            "Day's Low",
            "Avg Vol (10-day)", 
            #"52-Wk Range", 
            "Annual Dividend/Yield",
            "New Constructs Score"
            ]

    # Drop feature description column if flag is False (default)
    if return_full == False:
        temp.drop(index=drop, columns=[0], inplace=True, errors='ignore')
    
    # Clean data
    temp = temp.T
    # Only one of these columns will be present:
    try:
        temp['% Below High'] = temp['% Below High'].map(lambda x: float(x.strip('%'))/100, na_action='ignore')
    except:
        temp['% Above Low'] = temp['% Above Low'].map(lambda x: clean(x), na_action='ignore')
    
    temp['% Held by Institutions'] = temp['% Held by Institutions'].map(lambda x: clean(x)/100, na_action='ignore')
    temp['Short Interest'] = temp['Short Interest'].map(lambda x: clean(x)/100, na_action='ignore')
    # Set list of columns for cleaing
    try_to_clean = ['Prev Close',
                    'Ask close',
                    'Bid close',
                    'Beta',
                    'Ask',
                    'Bid',
                    'EPS (TTM, GAAP)',
                    'Last Trade',
                    'Last (size)',
                    price_feat,
                    'Historical Volatility',
                    'P/E Ratio (TTM, GAAP)',
                    "Today's Open",
                    'Volume',
                    'Volume 10-day Avg']
    # Clean columns
    for col in try_to_clean:
        try:
            temp[col] = temp[col].map(lambda x: clean(x), na_action='ignore')
        except:
            pass
    
    # Convert date info to datetime if it exists
    if dividend_given:
        try:
            temp['Ex-dividend'] = pd.to_datetime(temp['Ex-dividend Date'], infer_datetime_format=True)
        except:
            temp['Ex-dividend'] = pd.to_datetime(temp['Ex-dividend'], infer_datetime_format=True)
        temp['Dividend Pay Date'] = pd.to_datetime(temp['Dividend Pay Date'], infer_datetime_format=True)

    # Try to force any remaining numbers to floats:
    temp = temp.astype('float64', errors='ignore')
    temp = temp.T   
    temp.sort_index(inplace=True)

    return temp

def scrape_earnings(driver, ticker, search_first=True, internet_speed='fast'):
    """
    This function scrapes the "Earnings" tab of a TD Ameritrade security
    lookup page
    :param driver: (Selenium webdriver) webdriver returned from start_bot()
    :param ticker: (str) ticker symbol to scrape
    :param search_first: (bool) allows for chain of scrapes to be done on one
                                security when set to False. Leave set to True
                                unless you are sure you are already on the
                                desired security, or the wrong data will scrape
    :param internet_speed: (str) set to 'slow' if bot is not working properly due
                                to slow page loading times.
    """
    # Search for symbol if flag is True
    if search_first:
        search_symbol(driver, ticker)
        if internet_speed == 'slow':
            time.sleep(1)

    if internet_speed == 'fast':
        sleep_time = 1
    elif internet_speed == 'slow':
        sleep_time = 2
    
    # Find main iframe:  
    driver.switch_to.default_content()    
    iframes = WebDriverWait(driver, 10).until(lambda x: x.find_elements(By.TAG_NAME, "iframe"))
    driver.switch_to.frame(iframes[3])
    
    # Switch to Earnings tab:
    WebDriverWait(driver,10).until(lambda x: x.find_element(By.XPATH, '//*[@id="layout-full"]/nav/ul/li[4]/a')).click()
    time.sleep(2)
    
    # Switch to Earnings Analysis (1st sub tab)
    WebDriverWait(driver,10).until(lambda x: x.find_element(By.XPATH, '//*[@id="layout-full"]/div[4]/nav/nav/a[1]')).click()
    time.sleep(sleep_time)
    
    # Wait for conditions before making soup
    WebDriverWait(driver, 10).until(lambda x: EC.text_to_be_present_in_element(x, 'Annual Earnings History and Estimates'))
    element = driver.find_element(By.XPATH, '//*[@id="main-chart-wrapper"]')
    WebDriverWait(driver, 10).until(lambda x: EC.visibility_of_element_located(element))
    
    # Make soup and find container/elements
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    earn_dict = {}
    earnings_dict = {}
    contain = soup.find('div', {'data-module-name':'EarningsAnalysisModule'})
    header = contain.find('div', {'class':'row contain earnings-data'})
    #key = header.find('td', {'class':'label bordered'}).get_text()
    earn_dict['Next Earnings Announcement'] = header.find('td', {'class':'value week-of'}).get_text()
    
    # Get number of analysts reporting on security
    analysts = header.find_all('td', {'class':'label'})[1].get_text().split()
    for word in analysts:
        # The number of analysts will be the only numerical string
        try:
            earn_dict['Growth Analysts'] = float(word)
        except:
            continue
    # Find chart object in container, then bars
    chart = contain.find('div', {'id':'main-chart-wrapper'})
    bars = chart.find_all('div', {'class':'ui-tooltip'})
    for bar in bars:
        text = bar.get_text('|').split('|')
        # text[0] is the year
        year = text[0]
        earnings_dict[year] = {}
        # There is more text when there is a earnings surprise
        if len(text) > 4:
            earnings_dict[year]['Earnings Result'] = text[1]
            earnings_dict[year][text[2].strip('"').strip().strip(':')] = float(text[3].replace('$',''))
            earnings_dict[year][text[4].split(':')[0]] = text[4].split(':')[1].strip()
        else:
            earnings_dict[year]['Earnings Result'] = 'Neutral'
            # Should be a string: 'Actual' or 'Estimate'
            est_string = text[1].strip('"').strip().strip(':')
            # The actual consensus estimate
            est = float(text[2].replace('$',''))
            earnings_dict[year][est_string] = est
            # Should be a string: 'Estimate range'
            est_range_string = text[3].split(':')[0]
            # The estimate range as a string
            est_range = text[3].split(':')[1].strip()
            # Convert to 
            earnings_dict[year][est_range_string] = est_range
            
    # Create df and all useful columns
    earnings_yrly = pd.DataFrame.from_dict(earnings_dict, orient='index')
    earnings_yrly['Growth'] = earnings_yrly['Actual'].pct_change()
    earnings_yrly['Low Estimate'] = earnings_yrly['Estimate range'].map(lambda x: float(x.split()[0].replace('$','')), na_action='ignore')
    earnings_yrly['Low Growth Est'] = earnings_yrly['Low Estimate'].pct_change()
    earnings_yrly['High Estimate'] = earnings_yrly['Estimate range'].map(lambda x: float(x.split()[2].replace('$','')), na_action='ignore')
    earnings_yrly['High Growth Est'] = earnings_yrly['High Estimate'].pct_change()
    # Take average of high and low for years where 'Estimate' not available
    earnings_yrly['Consensus Estimate'] = (earnings_yrly['High Estimate'] + earnings_yrly['Low Estimate']) / 2
    # Supercede these values where consensus estimates are available
    idx_to_change = earnings_yrly[earnings_yrly['Estimate'].notnull()].index
    earnings_yrly.loc[idx_to_change, 'Consensus Estimate'] = earnings_yrly.loc[idx_to_change, 'Estimate']
    # Make new column that contains the actuals and consensus estimates
    earnings_yrly['Actual/Estimate'] = earnings_yrly['Actual']
    earnings_yrly.loc[idx_to_change, 'Actual/Estimate'] = earnings_yrly.loc[idx_to_change, 'Estimate']
    earnings_yrly['A/E Growth'] = earnings_yrly['Actual/Estimate'].pct_change()

    if 'Consensus estimate' in earnings_yrly.columns:
        # Sometimes ranges aren't given, and Consensus estimate given instead, fill holes caused
        earnings_yrly['Consensus Estimate'].fillna(earnings_yrly[earnings_yrly['Consensus estimate'].notnull()]['Consensus estimate'].map(lambda x: float(x.replace('$',''))), inplace=True)
        earnings_yrly.drop(columns=['Consensus estimate'], inplace=True)
    earnings_yrly.drop(columns=['Estimate range'], inplace=True)
    earnings_yrly['Consensus Growth Est'] = (earnings_yrly['High Growth Est']+earnings_yrly['Low Growth Est']) / 2
    
    low_1yr_growth_est = earnings_yrly.iloc[-2,:]['Low Growth Est']
    high_1yr_growth_est = earnings_yrly.iloc[-2,:]['High Growth Est']
    cons_1yr_growth_est = earnings_yrly.iloc[-2,:]['Consensus Growth Est']
    growth_2yr_low_est = earnings_yrly.iloc[-2:]['Low Growth Est'].mean()
    growth_2yr_high_est = earnings_yrly.iloc[-2:]['High Growth Est'].mean()
    growth_2yr_cons_est = (growth_2yr_low_est + growth_2yr_high_est) / 2
    earn_dict['Growth 1yr Low Est'] = low_1yr_growth_est
    earn_dict['Growth 1yr High Est'] = high_1yr_growth_est
    earn_dict['Growth 1yr Consensus Est'] = cons_1yr_growth_est
    earn_dict['Growth 2yr Low Est'] = growth_2yr_low_est
    earn_dict['Growth 2yr High Est'] = growth_2yr_high_est
    earn_dict['Growth 2yr Consensus Est'] = growth_2yr_cons_est
    earn_dict['Growth 5yr Low Est'] = earnings_yrly['Low Growth Est'].mean()
    earn_dict['Growth 5yr High Est'] = earnings_yrly['High Growth Est'].mean()
    earn_dict['Growth 5yr Consensus Est'] = earnings_yrly['Consensus Growth Est'].mean()
    earn_dict['Growth 5yr Actual/Est'] = earnings_yrly['A/E Growth'].mean()
    earn_dict['Growth 3yr Historic'] = earnings_yrly['Growth'].mean()

    earn_df = pd.DataFrame.from_dict(earn_dict, orient='index', columns=[ticker])
    earn_df[ticker] = earn_df[ticker].map(clean)

    return earn_df, earnings_yrly

def scrape_fundamentals(driver, ticker, search_first=True, internet_speed='fast'):
    """
    This function scrapes the "Fundamentals" tab of a TD Ameritrade security
    lookup page
    :param driver: (Selenium webdriver) webdriver returned from start_bot()
    :param ticker: (str) ticker symbol to scrape
    :param search_first: (bool) allows for chain of scrapes to be done on one
                                security when set to False. Leave set to True
                                unless you are sure you are already on the
                                desired security, or the wrong data will scrape
    :param internet_speed: (str) set to 'slow' if bot is not working properly due
                                to slow page loading times.
    """
    # Search symbol first if flag is True
    if search_first:
        search_symbol(driver, ticker)
        #tabs = get_tab_links()
    
    if internet_speed == 'fast':
        sleep_time = 1
    elif internet_speed == 'slow':
        sleep_time = 2
        time.sleep(1)

    # Gets Overview
    driver.switch_to.default_content()
    iframes = WebDriverWait(driver, 10).until(lambda x: x.find_elements(By.TAG_NAME,"iframe"))
    driver.switch_to.frame(iframes[3])
    WebDriverWait(driver,10).until(lambda x: x.find_element(By.XPATH, '//*[@id="layout-full"]/nav/ul/li[5]/a')).click()
    #time.sleep(1)
    WebDriverWait(driver,10).until(lambda x: x.find_element(By.XPATH, '//*[@id="layout-full"]/div[4]/nav/nav/a[1]')).click()
    time.sleep(sleep_time)
    driver.switch_to.default_content()
    iframes = WebDriverWait(driver, 10).until(lambda x: x.find_elements(By.TAG_NAME, "iframe"))
    driver.switch_to.frame(iframes[3])
    #WebDriverWait(driver, 10).until(lambda x: EC.text_to_be_present_in_element(x, 'Price Performance'))
    #driver.find_element_by_xpath('//*[@id="layout-full"]/nav/ul/li[5]/a').click()
    #time.sleep(1)

    # Wait for conditions before making soup
    WebDriverWait(driver, 10).until(lambda x: EC.text_to_be_present_in_element(x, 'Price Performance'))
    element = driver.find_element(By.XPATH, '//*[@id="price-charts-wrapper"]/div')
    WebDriverWait(driver, 10).until(lambda x: EC.visibility_of_element_located(element))
      
    # Make soup
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    # Scrapes current valuation ratios
    contain = soup.find('div', {'class': 'ui-description-list'})
    labels = [x.get_text().strip() for x in contain.find_all('dt')]
    values = [float(x.get('data-rawvalue')) for x in contain.find_all('dd')]
    for i, value in enumerate(values):
        if value == '-99999.99' or value == -99999.99:
            values[i] = np.NaN
    fundies = dict(zip(labels,values))

    # Gets 5yr low and high from chart
    contain = soup.find('div', {'class':'col-xs-8 price-history-chart'})
    five_yr = contain.find_all('div', {'class':'marker hideOnHover'})
    fundies['5yr Low'] = five_yr[0].get_text().split(' ')[1]
    fundies['5yr High'] = five_yr[1].get_text().split(' ')[1]

    # Gets 5 year Price Performance data from each hover section of graphic
    periods = contain.find_all('div', {'class':'period'})
    texts = [x.get_text('|') for x in periods]
    past_dict = {}
    yr_growths = []
    for text in texts:
        parts = text.split('|')
        year = parts[2].split(' ')[3].strip()
        past_dict[year] = {}
        high = parts[1].split(' ')[2].strip()
        low = parts[0].split(' ')[2].strip()
        change = parts[2].split(' ')[0].strip()
        past_dict[year]['high'] = high
        past_dict[year]['low'] = low
        past_dict[year]['change'] = change
        yr_growths.append(float(change.strip('%')))
    fundies['5yr Avg Return'] = np.mean(yr_growths) / 100

    # Gets Historic Growth and Share Detail
    contain = soup.find('div', {'data-module-name':'HistoricGrowthAndShareDetailModule'})
    boxes = contain.find_all('div', {'class':'col-xs-4'})
    labels = []
    values = []
    historic_data = True

    for box in boxes:
        numbers = []
        words = []
        if box.find('h4').get_text() == 'Historic Growth':
            for dt in box.find_all('dt')[1:]:
                word = dt.get_text('|').split('|')[0].strip() +' Growth 5yr'
                words.append(word)
            for dd in box.find_all('dd'):
                try:
                    number = float(dd.find('label').get('data-value'))
                    #print(number)
                    if number == -99999.99:
                        #print("here")
                        number = np.NaN
                except:
                    #print("didn't find number")
                    try:
                        number = dd.find('span').get_text()
                    except:
                        number = np.NaN
                #print(number)
                numbers.append(number)
            if len(words) == 0:
                print("Historic Growth not available for {}".format(ticker))
                historic_data = False
        else:
            for dt in box.find_all('dt')[1:]:
                word = dt.get_text('|').split('|')[0].strip()
                words.append(word)
            for dd in box.find_all('dd'):
                try:
                    number = float(dd.get('data-rawvalue'))
                    if number == -99999.99:
                        number = np.NaN
                except:
                    try:
                        number = dd.get_text()
                    except:
                        number = np.NaN
                numbers.append(number)

        labels = labels + words
        values = values + numbers
    
    # Make df of Historic Growth and Share Detail
    fundies2 = dict(zip(labels, values))

    # Get ready to scrape financial reports:
    report_names = ['Balance Sheet',
              'Income Statement',
              'Cash Flow'
             ]
    xpaths = [#'//*[@id="layout-full"]/div[4]/nav/nav/a[1]', # Already done
              '//*[@id="layout-full"]/div[4]/nav/nav/a[2]',
              '//*[@id="layout-full"]/div[4]/nav/nav/a[3]',
              '//*[@id="layout-full"]/div[4]/nav/nav/a[4]'
             ]
    reports = dict(zip(report_names, xpaths))
    
    # Function to scrape each report, since their formats are similar enough
    def scrape_report(name, xpath):
        # Switch to Appropriate Report
        driver.find_element(By.XPATH, xpath).click()
        time.sleep(sleep_time)
        iframes = WebDriverWait(driver, 10).until(lambda x: x.find_elements(By.TAG_NAME, "iframe"))
        driver.switch_to.frame(iframes[3])
        driver.switch_to.default_content()
        iframes = WebDriverWait(driver, 10).until(lambda x: x.find_elements(By.TAG_NAME, "iframe"))
        driver.switch_to.frame(iframes[3])
        WebDriverWait(driver, 10).until(lambda x: EC.text_to_be_present_in_element(x, 'Values displayed are in millions.'))
        element = driver.find_element(By.XPATH, '//*[@id="layout-full"]/div[4]/div/div')
        WebDriverWait(driver, 10).until(lambda x: EC.visibility_of_element_located(element))

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        #pprint.pprint(soup)
        contain = soup.find('div', {'data-module-name':'FinancialStatementModule'})
        year_info = [x.get_text('|') for x in contain.find_all('th', {'scope':'col'})]
        years = [x.split('|')[0] for x in year_info]
        dates = [x.split('|')[1] for x in year_info]

        sheet = {}
        for i, year in enumerate(years):
            sheet[year] = {}
            sheet[year]['Date'] = dates[i]
        row_names = []
        contain = soup.find('div', {'class':'row contain data-view'})
        rows = contain.find_all('tr')[1:] # Skips the header row
        #rows = contain.find_all('th', {'scope':'row'})
        for row in rows:
            #print(row)
            row_name = row.get_text('|').split('|')[0]
            row_names.append(row_name)
            values = row.find_all('td')
            for i, value in enumerate(values):
                sheet[years[i]][row_name] = value.get_text()
                
        temp = pd.DataFrame.from_dict(sheet, orient='index').T
        temp['Report'] = name
        return temp
    
    
    # Create summary dataframes
    temp = pd.DataFrame.from_dict(fundies, orient='index', columns=[ticker])
    temp2 = pd.DataFrame.from_dict(fundies2, orient='index', columns=[ticker])
    temp2.rename(index={'Current Month':'Short Int Current Month',
                         'Previous Month':'Short Int Prev Month',
                         'Percent of Float':'Short Int Pct of Float'
                        },
                inplace=True)
    # Clean these rows if they exist
    try:
        temp2.loc['Short Int Pct of Float',:] = temp2.loc['Short Int Pct of Float',:].astype('float64') / 100
        temp2.loc['% Held by Institutions',:] = temp2.loc['% Held by Institutions',:].astype('float64') / 100
    except:
        print("Short Interest info not available for {}".format(ticker))

    # Create yearly dataframe
    yearly = pd.DataFrame.from_dict(past_dict, orient='index').T
    for name, xpath in reports.items():
        tempy = scrape_report(name, xpath)
        yearly = pd.concat([yearly, tempy], axis=0, sort=False)
    
    # Combine two summary dataframes
    temp = pd.concat([temp,temp2], axis=0) 

    # Clean data in the dataframes  
    for col in temp:
        temp[col] = temp[col].map(lambda x: clean(x),  na_action='ignore')
    colnames = [col for col in yearly.columns if col not in ['Report']]
    for col in colnames:
        yearly[col] = yearly[col].map(lambda x: clean(x), na_action='ignore')
    
    # Create FCF and growth features for summary from yearly:
    yearly = yearly.T.astype('float64', errors='ignore')
    temp = temp.T.astype('float64', errors='ignore')
    indices = [indx for indx in yearly.index if indx not in ['Report']]
    yearly['Free Cash Flow'] = np.NaN
    yearly['FCF Growth'] = np.NaN
    # Allows this to not throw errors if values not available
    try:
        yearly.loc[indices,'Free Cash Flow'] = yearly.loc[indices,'Total Cash from Operations'] + yearly['Capital Expenditures']
        yearly.loc[indices,'FCF Growth'] = yearly.loc[indices,'Free Cash Flow'].pct_change()
        temp['FCF Growth 5yr'] = yearly['FCF Growth'].mean()
    except:
        temp['FCF Growth 5yr'] = np.NaN
    # These percentages must be formatted
    if historic_data:
        temp['EPS Growth 5yr'] = temp['EPS Growth 5yr']/100
        temp['Revenue Growth 5yr'] = temp['Revenue Growth 5yr']/100
        temp['Dividend Growth 5yr'] = temp['Dividend Growth 5yr']/100
    else:
        temp['EPS Growth 5yr'] = np.NaN
        temp['Revenue Growth 5yr'] = np.NaN
        temp['Dividend Growth 5yr'] = np.NaN

    # Transposing dataframes back
    temp = temp.T
    yearly = yearly.T

    return temp, yearly

def scrape_valuation(driver, ticker, search_first=True, internet_speed='fast'):
    """
    This function scrapes the "Valuation" tab of a TD Ameritrade security
    lookup page
    :param driver: (Selenium webdriver) webdriver returned from start_bot()
    :param ticker: (str) ticker symbol to scrape
    :param search_first: (bool) allows for chain of scrapes to be done on one
                                security when set to False. Leave set to True
                                unless you are sure you are already on the
                                desired security, or the wrong data will scrape
    :param internet_speed: (str) set to 'slow' if bot is not working properly due
                                to slow page loading times.
    """
    # Search symbol first if flag is True
    if search_first:
        search_symbol(driver, ticker)

    if internet_speed == 'fast':
        sleep_time = 2
    elif internet_speed == 'slow':
        sleep_time = 3
        time.sleep(1)
    # Find main iframe
    driver.switch_to.default_content()
    iframes = WebDriverWait(driver, 10).until(lambda x: x.find_elements(By.TAG_NAME, "iframe"))
    driver.switch_to.frame(iframes[3])

    # Switch to Valuation tab
    WebDriverWait(driver, 10).until(lambda x: x.find_element(By.XPATH, '//*[@id="layout-full"]/nav/ul/li[6]/a')).click()
    #time.sleep(1)

    # Switch to First tab under Valuation (also Valuation)
    WebDriverWait(driver,10).until(lambda x: x.find_element(By.XPATH, '//*[@id="stock-valuationmodule"]/div/div[1]/nav/a[1]')).click()
    driver.switch_to.default_content()
    iframes = WebDriverWait(driver, 10).until(lambda x: x.find_elements(By.TAG_NAME, "iframe"))
    driver.switch_to.frame(iframes[3])

    # Wait for condition before advancing
    WebDriverWait(driver, 10).until(lambda x: EC.text_to_be_present_in_element(x, '{} vs Industry'.format(ticker)))
    
    # Prepare to scrape valuation tabs by xpath
    tab_names = ['Valuation',
                 'Profitability',
                 'Dividend',
                 'Gowth rates',
                 'Effectiveness',
                 'Financial strength'
                ]
    xpaths = ['//*[@id="stock-valuationmodule"]/div/div[1]/nav/a[1]',
              '//*[@id="stock-valuationmodule"]/div/div[1]/nav/a[2]',
              '//*[@id="stock-valuationmodule"]/div/div[1]/nav/a[3]',
              '//*[@id="stock-valuationmodule"]/div/div[1]/nav/a[4]',
              '//*[@id="stock-valuationmodule"]/div/div[1]/nav/a[5]',
              '//*[@id="stock-valuationmodule"]/div/div[1]/nav/a[6]'
             ]
    tabs = dict(zip(tab_names, xpaths))

    # Scrape each tab
    valuation_df = pd.DataFrame()
    for name, xpath in tabs.items():
        # Switch to Appropriate Report
        driver.find_element(By.XPATH, xpath).click()
        iframes = WebDriverWait(driver, 10).until(lambda x: x.find_elements(By.TAG_NAME, "iframe"))
        driver.switch_to.frame(iframes[3])
        driver.switch_to.default_content()
        iframes = WebDriverWait(driver, 10).until(lambda x: x.find_elements(By.TAG_NAME, "iframe"))
        driver.switch_to.frame(iframes[3])
        WebDriverWait(driver, 10).until(lambda x: EC.text_to_be_present_in_element(x, '{} vs Industry'.format(ticker)))
        element = WebDriverWait(driver, 10).until(lambda x: x.find_element(By.XPATH, '//*[@id="stock-valuationmodule"]/div/div[1]/div[2]'))
        WebDriverWait(driver, 10).until(lambda x: EC.text_to_be_present_in_element(x, '{} Analysis'.format(name)))
        time.sleep(sleep_time)
        # Prevents breaking when there is no info on a tab, by waiting for condition
        try:
            element = driver.find_element(By.XPATH, '//*[@id="stock-valuationmodule"]/div/div/div[2]/table/tbody/tr[1]/td[2]')
            WebDriverWait(driver, 10).until(lambda x: EC.visibility_of_element_located(element))
        except:
            continue

        # Make soup and find container
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        contain = soup.find('div', {'data-module-name':'StocksValuationModule'})
        
        # Get data
        row_names = [x.get_text() for x in contain.find_all('a', {'class':'definition-link'})]
        tds = soup.find_all('td', {'class':'data-compare'})
        value_dict = {}
        for i, row_name in enumerate(row_names[1:]):
            value_dict[row_name] = {}
            dts = tds[i].find_all('dt')
            dds = tds[i].find_all('dd')
            cols = [dt.get_text() for dt in dts]
            vals = [dd.get_text() for dd in dds]
            value_dict[row_name][cols[0]] = vals[0]
            value_dict[row_name][cols[1]] = vals[1]
            value_dict[row_name]['Type'] = name

        # Create dataframe
        temp = pd.DataFrame.from_dict(value_dict, orient='columns').T
        valuation_df = pd.concat([valuation_df, temp], axis=0, sort=False)
    
    # Clean all columns except 'Type'
    for col in valuation_df.columns:
        if col != 'Type':
            valuation_df[col] = valuation_df[col].apply(lambda x: clean(x))

    # Create ratio to industry feature for normalized feature
    valuation_df['Ratio to Industry'] = valuation_df[ticker] / valuation_df['Industry']
    
    return valuation_df

def scrape_analysts(driver, ticker, search_first=True, internet_speed='fast'):
    """
    This function scrapes the "Analyst Reports" tab of a TD Ameritrade security
    lookup page
    :param driver: (Selenium webdriver) webdriver returned from start_bot()
    :param ticker: (str) ticker symbol to scrape
    :param search_first: (bool) allows for chain of scrapes to be done on one
                                security when set to False. Leave set to True
                                unless you are sure you are already on the
                                desired security, or the wrong data will scrape
    :param internet_speed: (str) set to 'slow' if bot is not working properly due
                                to slow page loading times.
    """
    # Search symbol first if flag is True
    if search_first:
        search_symbol(driver, ticker)

        if internet_speed == 'slow':
            time.sleep(1)

    if internet_speed == 'fast':
        sleep_time = 1
    elif internet_speed == 'slow':
        sleep_time = 2
    # Find iframe with tabs (main iframe)
    driver.switch_to.default_content()
    iframes = WebDriverWait(driver, 10).until(lambda x: x.find_elements(By.TAG_NAME, "iframe"))
    driver.switch_to.frame(iframes[3])

    # Switch to Analyst Reports tab
    WebDriverWait(driver, 10).until(lambda x: EC.text_to_be_present_in_element(x, 'Summary'))
    driver.find_element(By.XPATH, '//*[@id="layout-full"]/nav/ul/li[8]/a').click()
    time.sleep(sleep_time)

    # Wait for conditions before soup is made
    driver.switch_to.default_content()
    iframes = WebDriverWait(driver, 10).until(lambda x: x.find_elements(By.TAG_NAME, "iframe"))
    driver.switch_to.frame(iframes[3])
    WebDriverWait(driver, 10).until(lambda x: EC.text_to_be_present_in_element(x, 'Archived Reports'))

    # Make soup and find container and elements
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    contain = soup.find('table', {'class':'ui-table provider-table'}).find('tbody')
    trs = contain.find_all('tr')

    analysts = []
    ratings = []
    dates = []
    for tr in trs:
        divs = tr.find_all('div')
        analyst = divs[0].get('class')[1].strip()
        
        try:
            # Skip vickers
            if analyst == 'vickers':
                continue
            # Special treatment for marketEdge
            else:
                # Get date or NaN otherwise
                try:
                    txt = tr.find('p', {'class':'rating-since'}).get_text()
                    date = txt.replace('Rating Since ','')
                except:
                    date = np.NaN
                # Special treatment for marketEdge
                if analyst == 'marketEdge':
                    analysts.append(analyst+' opinion')
                    rating = divs[2].get('class')[2]
                    ratings.append(rating)
                    dates.append(date)
                    flag = False
                    i = 0
                    while flag == False:
                        i += 1
                        rating = divs[3].get('class')[1][-i].strip()
                        try:
                            rating = float(rating)
                            if i != 1:
                                rating = -rating
                            flag = True
                        except:
                            flag = False
                # Special treatment for cfra
                elif analyst == 'cfra':
                    rating = divs[2].get('class')[1][-1].strip()
                    try:
                        int(rating)
                    except:
                        rating = np.NaN
                else:
                    rating = divs[2].get('class')[1].strip()
                # Try to make ratings numeric
                try:
                    rating = int(rating)
                except:
                    rating = rating
        except:
            rating = np.NaN
            date = np.NaN

        analysts.append(analyst)
        ratings.append(rating)
        dates.append(date)

    # Create dataframe
    analyst_dict = dict(zip(analysts,zip(ratings,dates)))
    temp = pd.DataFrame.from_dict(analyst_dict, 
                                  orient='index', 
                                  columns=[ticker,'Rating Since'],
                                  )
    # Convert date column to datetime
    temp['Rating Since'] = pd.to_datetime(temp['Rating Since'], infer_datetime_format=True)
    
    return temp

def scrape_ticker(driver, ticker, errors='ignore', internet_speed='fast'):
    """
    This function scrapes every tab of a security based on ticker passed.
    Each scrape will be attempted 5 times before being skipped, as it is 
    unlikely for the data to fail to scrape this many times unless it is 
    truly absent.
    :param driver: (Selenium webdriver) webdriver returned from start_bot()
    :param ticker: (str) ticker symbol to scrape
    :param internet_speed: (str) set to 'slow' if bot is not working properly due
                                to slow page loading times.
    """
    # Getting Summary
    success = False
    tries = 0
    while not success:
        tries += 1
        try:
            summary = scrape_summary(driver, ticker, internet_speed=internet_speed)
            success = True
        except:
            print("Failed to gather summary for {} on attempt {}".format(ticker, tries))
        if tries >= 5:    
            print("Too many failed attempts for summary of {}, skipping to next df.".format(ticker))
            summary = pd.DataFrame(columns=[ticker])
            if errors == 'raise':
                raise
            elif errors == 'ignore':
                break

    # Getting Earnings
    success = False
    tries = 0
    while not success:
        tries += 1
        try:
            earnings, earnings_yearly = scrape_earnings(driver, ticker, search_first=False, internet_speed=internet_speed)
            success = True
        except:
            print("Failed to gather earnings for {} on attempt {}".format(ticker, tries))
        if tries >= 5:
            print("Too many failed attempts for earnings of {}, skipping to next df.".format(ticker))
            earnings = pd.DataFrame(columns=[ticker])
            earnings_yearly = pd.DataFrame(columns=[ticker])
            if errors == 'raise':
                raise
            elif errors == 'ignore':
                break
    
    # Getting fundamentals
    success = False
    tries = 0
    while not success:
        tries += 1
        try:
            fundies, fundies_yearly = scrape_fundamentals(driver, ticker, search_first=False, internet_speed=internet_speed)
            success = True
        except:
            print("Failed to gather fundamentals for {} on attempt {}".format(ticker, tries))
        if tries >= 5:
            print("Too many failed attempts for fundamentals of {}, skipping to next df.".format(ticker))
            fundies = pd.DataFrame(columns=[ticker])
            fundies_yearly = pd.DataFrame(columns=[ticker])
            if errors == 'raise':
                raise
            elif errors == 'ignore':
                break

    # Getting valuation
    success = False
    tries = 0
    while not success:
        tries += 1
        try:
            valuation = scrape_valuation(driver, ticker, search_first=False, internet_speed=internet_speed)
            success = True
        except:
            print("Failed to gather valuation for {} on attempt {}".format(ticker, tries))
        if tries >= 5:
            print("Too many failed attempts for valuation of {}, skipping to next df.".format(ticker))
            valuation = pd.DataFrame(columns=[ticker])
            if errors == 'raise':
                raise
            elif errors == 'ignore':
                break
    
    # Getting analyst reports
    success = False
    tries = 0
    while not success:
        tries += 1
        try:
            analysis = scrape_analysts(driver, ticker, search_first=False, internet_speed=internet_speed)
            success = True
        except:
            print("Failed to gather analysts for {} on attempt {}".format(ticker, tries))
        if tries >= 5:
            print("Too many failed attempts for analysts of {}, skipping to next df.".format(ticker))
            analysis = pd.DataFrame(columns=[ticker])
            if errors == 'raise':
                raise
            elif errors == 'ignore':
                break
    
    # Create combined 1D df for later stacking
    combined = pd.concat([summary[ticker].drop(index=['Shares Outstanding']),
                          earnings[ticker],
                          fundies[ticker],
                          valuation[ticker],
                          analysis[ticker]
                         ],
                        axis=0)
    # Remove duplicate rows from combined
    combined = pd.DataFrame(combined.loc[~combined.index.duplicated(keep='first')])
    for analyst in analysis.index:
        combined.loc[analyst+' since'] = analysis.loc[analyst, 'Rating Since']
    # Produce dictionary of results
    results = {'combined':combined, 
               'summary':summary, 
               'earnings':earnings, 
               'earnings_yearly':earnings_yearly, 
               'fundies':fundies, 
               'fundies_yearly':fundies_yearly, 
               'valuation':valuation,
               'analysts':analysis
              }
    return results

def scrape_watchlist(driver, tickers, name, root_dir='', skip_finished=True,
                     save_df=False, errors='ignore', return_skipped=False,
                     internet_speed='fast'):
    """
    Main wrapper function for scraper. Can do large lists of securities,
    and will store the data into assigned directory (can be set with kwarg)
    :param driver: selenium webdriver
    :param tickers: (list) ticker symbols
    :param name: (str) name of watchlist
    :param root_dir: (str) directory to save database to. Will use current working
                            directory if none passed.
    :param save_df: (bool) Whether to save the combined df to disk
    :param errors: (str) 'raise' or 'ignore'
    :param return_skipped: (bool) can return list of skipped securities if
                            ignoring errors
    :param internet_speed: (str) set to 'slow' if bot is not working properly due
                            to slow page loading times.
    """
    # Make list for skipped securities if needed
    if return_skipped == True:
        skipped = []

    # Create path name based on date and watchlist name, and make directory
    path_name = root_dir + name + '_' + datetime.today().strftime('%m-%d-%Y')
    # path_name = root_dir + name + '_' + datetime(2022, 11, 27).strftime('%m-%d-%Y')
    if not os.path.isdir(path_name):
        os.mkdir(path_name)
    
    # Create empty dataframe
    big_df = pd.DataFrame()
    
    # Scrape each ticker
    for i, ticker in enumerate(tickers):
        tickers_done = i + 1
        # Establish ticker path
        ticker_path = path_name+'/{}'.format(ticker)
        
        # Skip previously scraped securities if flag is True
        if skip_finished:
            if os.path.isdir(ticker_path):
                continue
        
        # Scrape security
        try:
            results = scrape_ticker(driver, ticker, errors=errors, internet_speed=internet_speed)
        except:
            print("Did not successfully scrape {}".format(ticker))
            if errors == 'raise':
                raise
            else:
                if return_skipped:
                    skipped.append(ticker)
                continue
        
        # Make directory if there is none
        if not os.path.isdir(ticker_path):
            os.mkdir(ticker_path)
        
        # Dump .csv files to directory
        for name, dataframe in results.items():
            try:
                dataframe.to_csv(ticker_path + '/{}'.format(name) + '.csv')
            except:
                print("No {} dataframe for {}".format(name,ticker))
        
        # Compile security to big_df
        big_df = pd.concat([big_df, results['combined'].T], axis=0, sort=True)
        
        # Print number of tickers completed every 10 completions
        if tickers_done % 10 == 0:
            print("{} tickers scraped".format(tickers_done))

    # Saves combined dataframe to file if called
    if save_df:
        big_df.to_csv(path_name + '/{}'.format('big_df.csv'))
    
    if not return_skipped:
        return big_df,
    else:
        return big_df, skipped

def build_big_df(tickers, database_path):
    """
    This function reads a previously scraped watchlist database at the provided
    path, and combines all of the 'combined.csv' files into one dataframe.
    :param tickers: (list-like) The securities to be gathered
    :param database_path: (str) The location of the database
    """
    big_df = pd.DataFrame()
    for ticker in tickers:
        file_path = database_path+'/{}/combined.csv'.format(ticker)
        try:
            temp = pd.read_csv(file_path, index_col='Unnamed: 0').T
        except:
            temp = pd.DataFrame(pd.read_csv(file_path)).T
        big_df = pd.concat([big_df, temp.astype('float64',errors='ignore')], axis=0, sort=True)
    new_df = pd.DataFrame()
    for col in big_df:
        new_df[col] = big_df[col].astype('float64', copy=True, errors='ignore')
    for col in new_df.columns:
        if col.endswith('since'):
            new_df[col] = pd.to_datetime(new_df[col], infer_datetime_format=True)
    
    return new_df