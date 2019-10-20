import gspread
from oauth2client.service_account import ServiceAccountCredentials
from bs4 import BeautifulSoup as bs
import requests
from pprint import pprint
from collections import defaultdict
from datetime import datetime

#returns number of seconds in day today
#for comparing time by integer than by string
def getTodaySecond():
    today = datetime.today()
    midnight = today.replace(hour=0,minute=0,second=0,microsecond=0)
    second = (today - midnight).seconds
    return second

# input spreadsheet, output array of titles
def spreadsheetTitles(spreadsheet):
    worksheets = spreadsheet.worksheets()
    titles = []
    for s in worksheets:
        titles.append(s.title)
    return titles

# takes titles on spreadsheet, names in spreadsheet, and spreadsheet
# void output, but adds unmade names to spreadsheet
def makeUnmadeTitles(titles, names, spreadsheet):
    titleSet = set(titles) # titles as a set
    nameSet = set(names) # names as a set
    unmade = nameSet - titleSet # unmade titles
    for name in unmade:
        spreadsheet.add_worksheet(name, 1000, 26)

# input is list of html, output is list of the text inside
def textOfList(arr):
    texts = []
    for html in arr:
        texts.append(html.text)
    return texts

# gets authorization to use api
scope = ["https://spreadsheets.google.com/feeds",'https://www.googleapis.com/auth/spreadsheets',"https://www.googleapis.com/auth/drive.file","https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("creds.json", scope)
client = gspread.authorize(creds)

todate = datetime.today()
today = todate.strftime("%b-%d-")
today += str(todate.year-2000)

spreadsheet = client.open("EASNYL") # spreadsheet base
titles = spreadsheetTitles(spreadsheet) # titles of each worksheet
linkSheet = spreadsheet.worksheet('Links') # spreadsheet with links and names
linkSheetContents = linkSheet.get_all_values() # contents of linkSheet
linkSheetContents.pop(0) # takes heading out
names = [row[0] for row in linkSheetContents] # names in the linkSheet
makeUnmadeTitles(titles, names, spreadsheet) # creates unmade titles
for row in linkSheetContents:
    urlBase = 'https://finviz.com/' # base for hrefs
    title = row[0] # title of worksheet
    worksheet = spreadsheet.worksheet(title) # worksheet to use
    link = row[1] # link in row
    html = requests.get(link).content # html of link
    soup = bs(html, 'lxml') # soup object of link
    table = soup.find(id='screener-content') # table with all contents
    newsURI = table.find('a', text='News')['href'] # URI to news section for scraping
    newsURL = [] # list for two news links
    newsURL.append(urlBase + newsURI) # url for news first 10
    newsURL.append(urlBase + newsURI + "&r=11") # url for news second 10
    header = table.find(valign='middle', align='center') # header of table, will be header of sheet
    header = header.findAll('td') # td tags of header, tags that have text
    headerTexts = textOfList(header) # texts inside header
    headerTexts.insert(0,'Date') # puts "Date" at the start
    headerTexts.append('News Headline') # puts "News Headling" at the end
    headerTexts.append('Hyperlink') # puts "Hyperlink" at the end
    worksheetHeader = worksheet.row_values(1) # header row of worksheet
    if(worksheetHeader != headerTexts): # checks if header is already there
        worksheet.insert_row(headerTexts) # puts header into sheet
    tickerNewsDict = defaultdict(list) # dictionary to get news articles
    currentHyperlinks = worksheet.col_values(len(headerTexts)) # list of hyperlinks in spreadsheet already
    for news in newsURL:
        newsHtml = requests.get(news).content # html of news section
        newsSoup = bs(newsHtml, 'lxml') # soup object of news
        for unit, symbol in zip(newsSoup.find_all('table', class_="body-table-news"), newsSoup.find_all(class_="snapshot-table")):
            ticker = symbol.a.text # ticker of news
            dateNews = unit.tr # tr tag that had date and news
            date = dateNews.td.text.split()[0] # date of news article, will be time if it differs by time
            if(date == today):
                info = dateNews.a # news info
                hyperlink = info['href'] # link to news article
                headline = info.text # headline of news article
                if(hyperlink not in currentHyperlinks):
                    tickerNewsDict[ticker] = [headline, hyperlink] # add to dictionary to later access
    tickersToCheck = tickerNewsDict.keys() # tickers that had news articles
    for row in table.find_all(True, {'class':['table-dark-row-cp', 'table-light-row-cp']}):
        ticker = row.td.text
        if ticker in tickersToCheck: # checks if this ticker has news
            rowInsert = [] # list to put into google sheets
            rowInsert.append(today) # put date at the start
            for info in row.find_all('td'):
                rowInsert.append(info.text) # adds info to list
            for x in tickerNewsDict[ticker]:
                rowInsert.append(x) # appends headline and hyperlink
            worksheet.insert_row(rowInsert, 2) # puts in spreadsheet
