import os
from os import listdir
from os.path import isfile, join
from datetime import datetime
import logging
import sys
import re

# Install PIL (https://pypi.org/project/Unidecode/)
# Mac		- pip install Unidecode
# Windows	- pip install Unidecode
from unidecode import unidecode

# Install PIL (https://pillow.readthedocs.io/en/5.1.x/installation.html)
# Mac		- pip install Pillow
# Windows	- pip install Pillow
from PIL import Image, ImageEnhance

# Install Wand (http://docs.wand-py.org/en/0.4.4/guide/install.html)
# Mac		- brew install imagemagick@6 (only v6 works with Wand)
#			- pip install Wand
# Windows 	- follow: http://docs.wand-py.org/en/0.4.4/guide/install.html#install-imagemagick-windows
#			- pip install Wand
#			- for pdf scraping install ghostscript: https://www.ghostscript.com/download/gsdnld.html
from wand.image import Image as wi

# Install tessaract (https://github.com/tesseract-ocr/tesseract/wiki)
# Mac 		- brew install tessaract
#			- pip install pytesseract
# Windows 	- get 4.0.0 from https://github.com/UB-Mannheim/tesseract/wiki
# 			- set tesseract as an envitonment variable
#			- pip install pytesseract
#
# Useful code reference (the nuts and bolts of how this works)
# https://github.com/nikhilkumarsingh/tesseract-python/blob/master/pdf_example.py
import pytesseract

# ------------------------------- #
# ----------- Logger ------------ #
# ------------------------------- #

# Configures logging to a 'logs.log'
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M',
                    filename='logs.log',
                    filemode='a')

# Creates the logger instance we will use to write logs
logger = logging.getLogger('logger')

# ------------------------------- #
# ---------- Variables ---------- #
# ------------------------------- #

# Define the current working directory (directory this is run from)
workingDirectory = os.getcwd()

# Define the directory name we will use to save temporary images we will be scraping
tempImageDirectoryName = 'pdfImageConversions'

# Define the directory name containing the pdf's
# This will default to the current working directory
pdfDirectory = input("What folder name contains the pdf's to scrape? (defaults to the current working directory): ")

# Define the directory the scraped pdf txt files should be saved
# This will default to '/renders'
renderDirectoryName = input("What filder name would you like to store the scraped text? (defaults to 'renders'): ")
renderDirectoryName = renderDirectoryName if renderDirectoryName else 'renders'

# Resolution of the image created from a pdf file
# The files do not interpret hand written or small text at 700 but its fairly quick
# To improve the scraped quality at the loss of scraping speed, increase the resolution by a few hundred
# Files will throw an exception when the render quality is too high ~900
# Tesseract actually works better with lower quality numbers around 200
resolution = input("what quality would you like the pdf's to scrape at? (defaults to 200, limit to ~600): ")
resolution = int(resolution) if resolution.isdigit() else 200

# File extension of the docuents we will save rendered text to
renderFileFormat = 'txt'

# Expressions tesseract will resolves as checked for check boxes
checkStrings = ['IXI', 'EI', 'M']

# Check box options
checkBoxOptions = ['YES', 'NO', 'Not Required']


# ----------------------------- #
# ---------- Methods ---------- #
# ----------------------------- #

# Saves the given text to a log file and prints it to the console
def log(content, level='info'):
    # log with the appropriate level
    if level is 'info':
        logger.info(content)
    if level is 'error':
        logger.error(content)
    if level is 'fatal':
        logger.fatal(content, exc_info=True)

    # print the message to the console
    print(content)


# Returns a pretty version of a paths base file name without its extension
def getAbsolutePathFileName(absolutePath=''):
    fileName = os.path.basename(absolutePath)
    fileName = fileName.split('.')[0]
    return fileName.replace(' ', '')


# Returns a string duration of now from a given time
def duration(startDuration):
    return str(datetime.now() - startDuration)


# True if a string is an integer
def stringIsInt(s):
    try:
        int(s)
        return True
    except ValueError:
        return False


# Gets a list of pdf file paths in a given directory.
# If no directory is provided, it will default to the current working directory
def getPdfFileNamesFromDirectory(directoryPath):
    try:
        # if a directory path is given we will use that
        directory = os.path.join(workingDirectory, directoryPath) if directoryPath else workingDirectory

        # create a list of pdf files in the file directory if it:
        # - is a valid file
        # - ends with '.pdf'
        return [os.path.join(directory, f) for f in listdir(directory) if isfile(join(directory, f)) if
                f.endswith('.pdf')]
    except Exception as ex:
        log(ex, 'fatal')
        sys.exit()


# Takes a tesseract data output and converts it to an array of pages containing an array of lines containing an
# array of columns
# Columns are:
# [0]level [1]page_num [2]block_num [3]par_num [4]line_num [5]word_num [6]left [7]top [8]width [9]height [10]conf
# [11]text [12] line_index
def getTesseractDataAsArrays(data):
    processedLines = []
    index = 0

    # Split the file into an array of lines
    lines = data.split('\n')

    for line in lines:
        # Clean up the line
        line.replace(',', '').replace('"', '')

        # Continue if the data line is blank
        if not line:
            continue

        # Split the line into an array of columns
        columns = line.split('\t')

        # No line if it has no value
        if len(columns) < 12 or not columns[11]:
            continue

        # Continue if the first column is text (that means its the data header)
        if not stringIsInt(columns[0]):
            continue

        # Add an index for the line
        columns.append(index)
        index += 1

        # The line at this point is valid
        processedLines.append(columns)

    return processedLines


# Constructs a regex grouped or expression as (i0|i1|i2) where i is the iterate of the array
def getArrayAsRegexOr(arr):
    return '(' + '|'.join(re.escape(x) for x in arr) + ')'


# Returns a clean version of a regex find and logs any error
def getCleanRegexSearch(expression, body, group):
    try:
        # '|' is a bitwise operator key
        searchResult = re.search(expression, body, re.M | re.I)
        if searchResult:
            searchResult = searchResult.group(group).lstrip().replace('\n', '')
        return searchResult
    except Exception as ex:
        log(ex, 'fatal')
    return False


# Finds text between two substrings for a given block of text.
# This will search over multiple lines and return a stripped string with no new line characters
def getTextBetweenStrings(start, end, body):
    # A regex to find text between two substrings over multiple lines
    searchRegex = r'' + re.escape(start) + '((.|\n)*?)' + re.escape(end)
    print(searchRegex)
    return getCleanRegexSearch(searchRegex, body, 1)


# Finds text after a substring for a given block of text.
# This will only return text for the line of the match
def getRemainingTextInString(match, body):
    # Determines if the match conditions are in a list
    isList = isinstance(match, list)

    # Ensure the match text is correctly formatted for the regex
    processedMatchText = getArrayAsRegexOr(match) if isList else re.escape(match)

    # A regex to find text after a given string
    searchRegex = r'' + processedMatchText + '(.*)$'

    # For convenience, within a list of matches we will return the remaining text and the matched
    return getCleanRegexSearch(searchRegex, body, 0 if isList else 1)


# Returns an answer for document questions
def getQuestionAnswer(question, documentString, answers):
    # Find the line of text containing your question
    questionLine = getRemainingTextInString(question, documentString)

    # Return nothing if there was no match
    if not questionLine:
        return None

    # Get the remaining text of the first checkbox that is checked
    checkText = getRemainingTextInString(checkStrings, questionLine)

    # Return nothing if there was no match
    if not checkText:
        return None

    # Find the answer for the checked box
    searchRegex = r'' + getArrayAsRegexOr(answers) + '(.*)$'
    matchedAnswer = getCleanRegexSearch(searchRegex, checkText, 1)

    return matchedAnswer


# Returns a list of lines which sequentially match a given string
def getDataLinesMatchingString(matchingString, data):
    # Strip the whitespace to ensure white spaces do not prevent matches
    matchingString = matchingString.replace(' ', '')
    lineMatches = []
    matchCopy = matchingString

    for line in data:
        # Do nothing if we find a match
        if not matchCopy:
            break
        else:
            # try find a match, if one is found we will add the matching line to our return list and remove that
            # text from  our matching text
            line[11] = line[11].replace(' ', '')

            # As we are looking for a sequence of matching lines, we should ensure that the line we check matches the
            # start of the remaining string.
            if matchCopy.find(line[11]) is 0:
                lineMatches.append(line)
                matchCopy = matchCopy.replace(line[11], '')
            else:
                lineMatches = []
                matchCopy = matchingString

    return lineMatches


# Gets the right coordinate of a data line
def getRightOfDataLine(line):
    return int(line[6]) + int(line[8])


# Gets the bottom coordinate of a data line
def getBottomOfDataLine(line):
    return int(line[7]) + int(line[9])


# Get the text contents of a table split by the column. All rows will be concat to the same string
def getTableColumns(
        preLines, postLines, ODFirstColumnHeader, ODLastColumnHeader, numberOfColumns, data, combineColumns=False):
    # Null check, parameters should have values.
    if not preLines \
            or not postLines \
            or not ODFirstColumnHeader \
            or not ODLastColumnHeader \
            or not numberOfColumns \
            or not data:
        return None

    # Step 1: Determine the width of the table columns assuming they will be the same width

    # Get the spacial difference between the left of the left column and the left of the first column header text
    # essentially: left coordinate of text minus left coordinate of table (assuming the pre text left == table left)
    columnOneHeaderGap = int(ODFirstColumnHeader[0][6]) - int(preLines[0][6])

    # Get the left position of the start of the pre lines (left position of table)
    leftOfColumnOne = int(preLines[0][6])
    # Get the right position of the first column
    # essentially: right of first column header + the gap between the text and the column side (assuming text justified)
    rightOfColumnOne = getRightOfDataLine(ODFirstColumnHeader[len(ODFirstColumnHeader) - 1]) + columnOneHeaderGap

    # Define the column widths assuming the columns are of equal width
    columnWidth = rightOfColumnOne - leftOfColumnOne

    # Step 2: Determine the rows we will be looping through for the table text

    startIndex = ODLastColumnHeader[len(ODLastColumnHeader) - 1][12] + 1
    endIndex = postLines[0][12] - 1
    tableRange = endIndex - startIndex

    # This is the array which will contain table column text
    tableText = '' if combineColumns else []

    # Loop through the data rows which contain text in the table
    for i in range(numberOfColumns):

        # Step 3: Determine the left and right coordinates for the column iterate

        columnNumber = i + 1
        columnLeft = leftOfColumnOne + ((columnNumber - 1) * columnWidth)
        columnRight = leftOfColumnOne + (columnNumber * columnWidth)

        # This is the string that will contain
        columnText = ''

        # Loop for the number of data rows that contain the table text
        for rowIndex in range(tableRange):

            # Step 4: Determine if the text of the data line is within the column. If true, add it to the column string

            # As the loop will start at 0 we need to offset to the table text data line
            loopIndex = startIndex + rowIndex + 1

            # Define the left and right coordinates of the line
            lineLeft = int(data[loopIndex][6])
            lineRight = lineLeft + int(data[loopIndex][8])

            # If the coordinates fit inside our column, add the text to our column string
            if lineLeft >= columnLeft and lineRight <= columnRight:
                columnText = columnText + ' ' + data[loopIndex][11]

        # Once we have looped through the table text data lines, add the column text to our table text array
        if combineColumns:
            tableText = tableText + ' ' + columnText.lstrip()
            tableText = tableText.lstrip()
        else:
            tableText.append(columnText.lstrip())

    # Return all table data in their respective columns
    return tableText


# Returns text from a pdf of a given path.
# The scraped pdf text files will be in a directory called rendered.
# If the pdf has been rendered the text will be returned
# From that file. If not, the pdf will be scraped, saved and the text returned.
def getFileExtract(readerFilePath):
    try:
        # Create a directory to store the rendered pdf's in
        renderDirectoryPath = os.path.join(workingDirectory, renderDirectoryName)

        # Create the directory to render files to if it does not exist
        if not os.path.exists(renderDirectoryPath):
            os.makedirs(renderDirectoryPath)

        # Define the name and path of the file we will be creating
        renderFileName = str(os.path.basename(readerFilePath).split('.')[0]) + '.' + str(renderFileFormat)
        renderFilePath = os.path.join(renderDirectoryPath, renderFileName)

        if not os.path.exists(renderFilePath):
            # If the render file exists we will create and write to it
            scrapedContent = scrapePdf(readerFilePath, renderFilePath)
        else:
            # Define the contents of the render file
            renderFile = open(renderFilePath, "r")
            renderFileContents = renderFile.read()
            renderFile.close()

            if not renderFileContents:
                # If the render file exists but is empty, we will write to it
                scrapedContent = scrapePdf(readerFilePath, renderFilePath)
            else:
                # If the render file exists and is populated, we will return its contents
                scrapedContent = renderFileContents

        # Split the data into the raw text extract and the informaion extract
        return scrapedContent.split('<data>')
    except Exception as ex:
        log(ex, 'fatal')
        sys.exit()


# Returns the text from a pdf.
# When the pdf is scraped, the contents will be saved to a given file path.
def scrapePdf(readerFilePath, renderFilePath):
    try:
        log("Beginning scrape of " + readerFilePath)

        # Create and open the file we will add the scraped text to
        with open(renderFilePath, "w+") as renderFile:
            log("Opened render file " + renderFilePath)

            # Open the pdf file to scrape
            with open(readerFilePath, "rb") as file:

                # Define the time we have started processing the pdf
                startTime = datetime.now()
                log("Opened the pdf")

                # Read the pdf file using 'Wand'
                with wi(file=file, resolution=resolution) as source:

                    print('read the pdf')

                    with source.convert('jpeg') as pdfImage:

                        # Get a nice version of the document file name
                        fileName = getAbsolutePathFileName(readerFilePath)

                        # Create the directory to render files to if it does not exist
                        if not os.path.exists(tempImageDirectoryName):
                            os.makedirs(tempImageDirectoryName)

                        log("Created the temporary directory used for storing temp pdf image conversions")

                        # Save the pdf pages as images. We save the iamges as it helps us debug potential issues with
                        # pdf conversions
                        source.save(filename=os.path.join(workingDirectory, tempImageDirectoryName, fileName + '.png'))
                        log("saved pdf pages as png's")

                        # Define the total number of pages in the pdf for logging
                        totalPages = len(pdfImage.sequence)

                        completeString = ''
                        completeData = ''

                        # Loop through each page opening the image and using tesseract to get the text
                        for i in range(0, totalPages):
                            # Construct the file name of the page we are iterating over
                            pageFileName = fileName + '-' + str(i) + '.png'
                            pagePath = join(workingDirectory, tempImageDirectoryName, pageFileName)

                            print(pagePath)
                            # Open the image

                            with Image.open(pagePath) as p:
                                p = p.convert('RGB')
                                # Attempt some basic image enhancements for scraping
                                enhancement = ImageEnhance.Sharpness(p)
                                p = enhancement.enhance(4.0)
                                enhancement = ImageEnhance.Contrast(p)
                                p = enhancement.enhance(2.0)
                                enhancement = ImageEnhance.Color(p)
                                p = enhancement.enhance(0.0)

                                # Save the enhanced image for comparison
                                p.save(os.path.join(workingDirectory, tempImageDirectoryName,
                                                    fileName + '-enhanced-' + str(i) + '.png'))

                                log("Opened saved image")

                                pageString = unidecode(pytesseract.image_to_string(p))
                                pageData = unidecode(pytesseract.image_to_data(p))

                                # Add the scraped text to our string for all text in the document
                                completeString = completeString + "\n" + pageString if completeString else pageString
                                completeData = completeData + "\n" + pageData if completeData else pageData

                                # Log the progress
                                log("Scraped page " + str(i + 1) + " / " + str(totalPages) + " of " + os.path.basename(
                                    readerFilePath))

                        # Save the scraped text and close the file
                        completeScrape = completeString + '\n' + '<data>' + '\n' + completeData

                        renderFile.write(completeScrape)
                        renderFile.close()

                        log("Complete scrape of '" + os.path.basename(readerFilePath) + "' in " + duration(startTime))

                        return completeScrape
    except Exception as ex:
        log(ex, 'fatal')
        sys.exit()


# ----------------------------- #
# ---------- Script ----------- #
# ----------------------------- #

# Define the absolute path of all pdf's in the given directory
pdfPaths = getPdfFileNamesFromDirectory(pdfDirectory)

# Define the total pdf's to scrape for logging
totalPdfs = len(pdfPaths)

# Store the start time of the process for logging
scrapeStart = datetime.now()

log("Beginning scrape of " + str(totalPdfs) + " pdf files in '" + pdfDirectory + "'")
log("Outputting redered files to /" + renderDirectoryName)
log("Render resolution set to " + str(resolution))

pdfData = {}

# For each absolute pdf path in the pdf directory:
for pdfIndex, path in enumerate(pdfPaths):
    # Get the text from the pdf (this will also save the text to a same named file in /renders)
    extract = getFileExtract(path)

    log("Complete " + str(pdfIndex + 1) + " / " + str(totalPdfs) + " total Pdf's")
    log("Current running time is " + duration(scrapeStart))

log("Completed scrape of pdf files in '" + pdfDirectory + "' in " + duration(scrapeStart))

print(pdfData)

# Terminate the script
sys.exit()
