from modules import customLogger
import sys
import os
from os import listdir
from os.path import isfile, join
from datetime import datetime

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


# Define the directory name we will use to save temporary images we will be scraping
tempImageDirectoryName = 'pdfImageConversions'


# Returns a pretty version of a paths base file name without its extension
def getAbsolutePathFileName(absolutePath=''):
    fileName = os.path.basename(absolutePath)
    fileName = fileName.split('.')[0]
    return fileName.replace(' ', '')


# Gets a list of pdf file paths in a given directory.
# If no directory is provided, it will default to the current working directory
def getPdfFileNamesFromDirectory(directory):
    try:

        # create a list of pdf files in the file directory if it:
        # - is a valid file
        # - ends with '.pdf'
        return [os.path.join(directory, f) for f in listdir(directory) if isfile(join(directory, f)) if
                f.endswith('.pdf')]
    except Exception as ex:
        customLogger.log(ex, 'fatal')
        sys.exit()


# Returns text from a pdf of a given path.
# The scraped pdf text files will be in a directory called rendered.
# If the pdf has been rendered the text will be returned
# From that file. If not, the pdf will be scraped, saved and the text returned.
def getFileExtract(readerFilePath, workingDirectory, renderDirectoryName, resolution):
    try:
        # Create a directory to store the rendered pdf's in
        renderDirectoryPath = os.path.join(workingDirectory, renderDirectoryName)

        # Create the directory to render files to if it does not exist
        if not os.path.exists(renderDirectoryPath):
            os.makedirs(renderDirectoryPath)

        # Define the name and path of the file we will be creating
        renderFileName = str(os.path.basename(readerFilePath).split('.')[0]) + '.txt'
        renderFilePath = os.path.join(renderDirectoryPath, renderFileName)

        if not os.path.exists(renderFilePath):
            # If the render file exists we will create and write to it
            scrapedContent = scrapePdf(readerFilePath, renderFilePath, resolution, workingDirectory)
        else:
            # Define the contents of the render file
            renderFile = open(renderFilePath, "r")
            renderFileContents = renderFile.read()
            renderFile.close()

            if not renderFileContents:
                # If the render file exists but is empty, we will write to it
                scrapedContent = scrapePdf(readerFilePath, renderFilePath, resolution, workingDirectory)
            else:
                # If the render file exists and is populated, we will return its contents
                scrapedContent = renderFileContents

        # Split the data into the raw text extract and the informaion extract
        return scrapedContent.split('<data>')
    except Exception as ex:
        customLogger.log(ex, 'fatal')
        sys.exit()


# Returns the text from a pdf.
# When the pdf is scraped, the contents will be saved to a given file path.
def scrapePdf(readerFilePath, renderFilePath, resolution, workingDirectory):
    try:
        customLogger.log("Beginning scrape of " + readerFilePath)

        # Create and open the file we will add the scraped text to
        with open(renderFilePath, "w+") as renderFile:
            customLogger.log("Opened render file " + renderFilePath)

            # Open the pdf file to scrape
            with open(readerFilePath, "rb") as file:

                # Define the time we have started processing the pdf
                startTime = datetime.now()
                customLogger.log("Opened the pdf")

                # Read the pdf file using 'Wand'
                with wi(file=file, resolution=resolution) as source:
                    with source.convert('jpeg') as pdfImage:

                        # Get a nice version of the document file name
                        fileName = getAbsolutePathFileName(readerFilePath)

                        # Create the directory to render files to if it does not exist
                        if not os.path.exists(tempImageDirectoryName):
                            os.makedirs(tempImageDirectoryName)

                        customLogger.log("Created the temporary directory used for storing temp pdf image conversions")

                        # Save the pdf pages as images. We save the iamges as it helps us debug potential issues with
                        # pdf conversions
                        source.save(filename=os.path.join(workingDirectory, tempImageDirectoryName, fileName + '.png'))
                        customLogger.log("saved pdf pages as png's")

                        # Define the total number of pages in the pdf for logging
                        totalPages = len(pdfImage.sequence)

                        completeString = ''
                        completeData = ''

                        # Loop through each page opening the image and using tesseract to get the text
                        for i in range(0, totalPages):
                            # Construct the file name of the page we are iterating over
                            pageFileName = fileName + '-' + str(i) + '.png'
                            pagePath = join(workingDirectory, tempImageDirectoryName, pageFileName)

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

                                customLogger.log("Opened saved image")

                                pageString = unidecode(pytesseract.image_to_string(p))
                                pageData = unidecode(pytesseract.image_to_data(p))

                                # Add the scraped text to our string for all text in the document
                                completeString = completeString + "\n" + pageString if completeString else pageString
                                completeData = completeData + "\n" + pageData if completeData else pageData

                                # Log the progress
                                customLogger.log("Scraped page " + str(i + 1) + " / " + str(totalPages) + " of " + os.path.basename(
                                    readerFilePath))

                        # Save the scraped text and close the file
                        completeScrape = completeString + '\n' + '<data>' + '\n' + completeData

                        renderFile.write(completeScrape)
                        renderFile.close()

                        # Delete the temporary image directory we used to save the images
                        # shutil.rmtree(join(workingDirectory, tempImageDirectoryName))

                        customLogger.log("Complete scrape of '"
                                         + os.path.basename(readerFilePath)
                                         + "' in "
                                         + customLogger.duration(startTime))

                        return completeScrape
    except Exception as ex:
        customLogger.log(ex, 'fatal')
        sys.exit()
