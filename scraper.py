import gspread
from oauth2client.service_account import ServiceAccountCredentials
from bs4 import BeautifulSoup as bs
import requests
from pprint import pprint
from collections import defaultdict
from datetime import datetime
import time

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

while(True):
    # gets authorization to use api
    scope = ["https://spreadsheets.google.com/feeds",'https://www.googleapis.com/auth/spreadsheets',"https://www.googleapis.com/auth/drive.file","https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("creds.json", scope)
    client = gspread.authorize(creds)

    #gets todays date and puts it in the correct format: Sep-20-19
    todate = datetime.today()
    today = todate.strftime("%b-%d-")
    today += str(todate.year-2000)

    # spreadsheet base
    spreadsheet = client.open("EASNYL")
    # titles of each worksheet
    titles = spreadsheetTitles(spreadsheet)
    # spreadsheet with links and names
    linkSheet = spreadsheet.worksheet('Links')
    # contents of linkSheet
    linkSheetContents = linkSheet.get_all_values()
    # takes heading out
    linkSheetContents.pop(0)
    # names in the linkSheet
    names = [row[0] for row in linkSheetContents]
    # creates unmade titles
    makeUnmadeTitles(titles, names, spreadsheet)
    for row in linkSheetContents:
        # base for hrefs
        urlBase = 'https://finviz.com/'
        # title of worksheet
        title = row[0]
        # worksheet to use
        worksheet = spreadsheet.worksheet(title)
        # link in row
        link = row[1]
        # html of link
        html = requests.get(link).content
        # soup object of link
        soup = bs(html, 'lxml')
        # table with all contents
        table = soup.find(id='screener-content')
        # URI to news section for scraping
        newsURI = table.find('a', text='News')['href']
        # list for two news links
        newsURL = []
        # url for news first 10
        newsURL.append(urlBase + newsURI)
        # url for news second 10
        newsURL.append(urlBase + newsURI + "&r=11")
        # header of table, will be header of sheet
        # changed to header1 temporarily
        header1 = table.find(valign='middle', align='center')
        
        # trying to catch attribute error and see html of such
        try:
            # td tags of header, tags that have text
            header = header1.find_all('td')
        except AttributeError:
            print("Table:")
            print(table)
            print()
            print("Header1:")
            print(header1)
            print()
            print("END ERROR")
        
        # texts inside header
        headerTexts = textOfList(header)
        # puts "Date" at the start
        headerTexts.insert(0,'Date')
        # puts "Time" in header
        headerTexts.insert(1,"Time")
        # puts "News Headling" at the end
        headerTexts.append('News Headline')
        # puts "Hyperlink" at the end
        headerTexts.append('Hyperlink')
        # header row of worksheet
        worksheetHeader = worksheet.row_values(1)
        # checks if header is already there
        if(worksheetHeader != headerTexts):
            # puts header into sheet
            worksheet.insert_row(headerTexts)
        # dictionary to get news articles
        tickerNewsDict = defaultdict(list)
        # list of hyperlinks in spreadsheet already
        currentHyperlinks = worksheet.col_values(len(headerTexts))
        # goes through each block of news on the page
        for news in newsURL:
            # html of news section
            newsHtml = requests.get(news).content
            # soup object of news
            newsSoup = bs(newsHtml, 'lxml')
            # unit gets the news data, symbol gets the ticker
            for unit, symbol in zip(newsSoup.find_all('table', class_="body-table-news"), newsSoup.find_all(class_="snapshot-table")):
                # ticker of news
                ticker = symbol.a.text
                # tr tag that had date and news
                dateNews = unit.tr
                # date and time of news article
                dateAndTime = dateNews.td.text.split()
                # separate the date
                date = dateAndTime[0]
                # separate the time
                timeOf = dateAndTime[1]
                # checks if the article is from today
                if(date == today):
                    # news <a> tag, has information about article
                    info = dateNews.a
                    # link to news article
                    hyperlink = info['href']
                    # headline of news article
                    headline = info.text
                    # checks if the hyperlink is already in the google sheet
                    if(hyperlink not in currentHyperlinks):
                        # add to dictionary to later access
                        tickerNewsDict[ticker] = [timeOf, headline, hyperlink]
        # tickers that had news articles
        tickersToCheck = tickerNewsDict.keys()
        # goes through each stock on the page
        for row in table.find_all(True, {'class':['table-dark-row-cp', 'table-light-row-cp']}):
            # ticker symbol of current row
            ticker = row.td.text
            # checks if this ticker has news
            if ticker in tickersToCheck:
                # list to put into google sheets
                rowInsert = []
                # put date at the start
                rowInsert.append(today)
                # time of article
                timeOf = tickerNewsDict[ticker][0]
                # put time after date
                rowInsert.append(timeOf)
                # goes through all the data from each stock
                for info in row.find_all('td'):
                    # adds info to list
                    rowInsert.append(info.text)
                # goes through each of the tickers info
                for x in range(1,3):
                    # info to append
                    unit = tickerNewsDict[ticker][x]
                    # appends headline and hyperlink
                    rowInsert.append(unit)
                # puts in spreadsheet
                worksheet.insert_row(rowInsert, 2)
    # waits 15 secs so to not call the API too many times
    time.sleep(60)