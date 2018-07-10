import re
from modules import customLogger


# True if a string is an integer
def stringIsInt(s):
    try:
        int(s)
        return True
    except ValueError:
        return False


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
        customLogger.log(ex, 'fatal')
    return False


# Finds text between two substrings for a given block of text.
# This will search over multiple lines and return a stripped string with no new line characters
def getTextBetweenStrings(start, end, body):
    # A regex to find text between two substrings over multiple lines
    searchRegex = r'' + re.escape(start) + '((.|\n)*?)' + re.escape(end)
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
def getQuestionAnswer(question, documentString, answers, checkStrings):
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
