import gspread
from oauth2client.service_account import ServiceAccountCredentials
from bs4 import BeautifulSoup as bs
import requests
from pprint import pprint
from collections import defaultdict
from datetime import datetime, timedelta
import time

#returns number of seconds in day today
#for comparing time by integer rather than by string
def getTodaySecond():
    # todays date
    today = datetime.today()
    # midnight as a reference point
    midnight = today.replace(hour=0,minute=0,second=0,microsecond=0)
    # today - 0 is total seconds
    second = (today - midnight).seconds
    return second

#gets second in time given
#time format: XX:XXPM/XX:XXAM
def getDaySecond(time):
    # separates hour and minutes
    timeElements = time.split(':')
    # condition of not 12 o'clock
    if int(timeElements[0]) != 12:
        if timeElements[1].endswith("AM"):
            hour = int(timeElements[0])
            mins = int(timeElements[1].strip("AM"))
        elif timeElements[1].endswith("PM"):
            hour = int(timeElements[0]) + 12
            mins = int(timeElements[1].strip("PM"))
    else:
        if timeElements[1].endswith("PM"):
            hour = int(timeElements[0])
            mins = int(timeElements[1].strip("PM"))
        if timeElements[1].endswith("AM"):
            hour = 0
            mins = int(timeElements[1].strip("AM"))
    seconds = hour * 60 * 60 + mins * 60
    return seconds

#returns the fiscal day today
#fiscal day runs between 4pm and 4pm
#hence, 4pm today is fiscal day tomorrow
def getFiscalDay():
    today = datetime.today()
    time = getTodaySecond()
    if time >= (4+12)*60*60:
        today += timedelta(days=1)
        fiscalDay = today.strftime("%b-%d-%y")
    else:
        fiscalDay = today.strftime("%b-%d-%y")
    return fiscalDay

#returns true if day and time given are within fiscal day
#4pm yesterday till 4pm today
#day format: AAA-XX-XX
#time format: XX:XXPM/XX:XXAM
def isFiscalDay(day, time):
    today = getFiscalDay()
    dateToCheck = datetime.strptime(day,"%b-%d-%y")
    daySeconds = getDaySecond(time)
    if daySeconds >= (4 + 12) * 60 * 60:
        dateToCheck += timedelta(days=1)
    dateToCheck = dateToCheck.strftime("%b-%d-%y")
    return True if (today == dateToCheck) else False

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

    #gets today's fiscal day
    today = getFiscalDay()

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
            print(datetime.now())
            print("Table:")
            print(table)
            print()
            print("Header1:")
            print(header1)
            print()
            print("END ERROR")
            continue
        
        # td tags of header, tags that have text
        header = header1.find_all('td')
        # header of website table
        headerTextsOriginal = textOfList(header)
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
        # worksheet header length
        worksheetHeaderLength = len(worksheetHeader)
        # checks if header is contains each header element
        for cell in headerTexts:
            # checks if header contains a cell in the header
            if(cell not in worksheetHeader):
                # puts header into sheet
                worksheet.insert_row(headerTexts)
                # updates worksheetHeader variable
                worksheetHeader = worksheet.row_values(1)
                #updates worksheetHeaderLength variable
                worksheetHeaderLength = len(worksheetHeader)
                # breaks so won't put header more than once
                break
        # dictionary for header index
        headerDict = {worksheetHeader[i]: i for i in range(0, worksheetHeaderLength)}
        # dictionary to get news articles
        tickerNewsDict = defaultdict(list)
        # list of hyperlinks in spreadsheet already
        currentHyperlinks = worksheet.col_values(headerDict["Hyperlink"]+1)
        # gets value in custom cells
        custom = []
        for heading in worksheetHeader:
            if(heading not in headerTexts):
                infoToAdd = []
                infoToAdd.append(heading)
                infoToAdd.append(worksheet.cell(2,headerDict[heading] + 1,"FORMULA").value)
                custom.append(infoToAdd)
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
                # <tr> has the date, time, and news
                for dateNews in unit.find_all('tr'):
                    # date and time of news article
                    dateAndTime = dateNews.td.text.split()
                    # separate the date
                    date = dateAndTime[0]
                    # separate the time
                    timeOf = dateAndTime[1]
                    # checks if the article is from today
                    if isFiscalDay(date,timeOf):
                        # news <a> tag, has information about article
                        info = dateNews.a
                        # link to news article
                        hyperlink = info['href']
                        # headline of news article
                        headline = info.text
                        # checks if the hyperlink is already in the google sheet
                        if(hyperlink not in currentHyperlinks):
                            # add to dictionary to later access
                            tickerNewsDict[ticker].append([date, timeOf, headline, hyperlink])
                    else:
                        break
        # tickers that had news articles
        tickersToCheck = list(tickerNewsDict.keys())
        # goes through each stock on the page
        for row in table.find_all(True, {'class':['table-dark-row-cp', 'table-light-row-cp']}):
            # incrementor for finding ticker
            i = 0
            # ticker symbol of current row
            for tag in row.find_all('td'):
                if i == headerTextsOriginal.index("Ticker"):
                    ticker = tag.text
                i += 1
            # checks if this ticker has news
            if ticker in tickersToCheck:
                for r in range(0,len(tickerNewsDict[ticker])):
                    # list to put into google sheets
                    rowInsert = [""] * worksheetHeaderLength
                    # put date at the start
                    rowInsert[headerDict["Date"]] = tickerNewsDict[ticker][r][0]
                    # time of article
                    rowInsert[headerDict["Time"]] = tickerNewsDict[ticker][r][1]
                    # article title
                    rowInsert[headerDict["News Headline"]] = tickerNewsDict[ticker][r][2]
                    # article hyperlink
                    rowInsert[headerDict["Hyperlink"]] = tickerNewsDict[ticker][r][3]
                    # goes through all the data from each stock
                    for info, head in zip(row.find_all('td'), headerTextsOriginal):
                        # adds info to list
                        rowInsert[headerDict[head]] = info.text
                    # adds custom info
                    for info in custom:
                        rowInsert[headerDict[info[0]]] = info[1]
                    # puts in spreadsheet
                    worksheet.insert_row(rowInsert, 2,"USER_ENTERED")
    # waits 60 secs so to not call the API too many times
    time.sleep(60)