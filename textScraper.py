import tempfile
import os
from os import listdir 
from os.path import isfile, join
from datetime import datetime
import logging
import sys
import base64
import io

# Install PIL (https://pillow.readthedocs.io/en/5.1.x/installation.html)
# Mac		- pip install Pillow
# Windows	- pip install Pillow
from PIL import Image

# Install Wand (http://docs.wand-py.org/en/0.4.4/guide/install.html)
# Mac		- brew install imagemagick@6 (only v6 works with Wand)
#			- pip install Wand
# Windows 	- follow: http://docs.wand-py.org/en/0.4.4/guide/install.html#install-imagemagick-windows
#			- pip install Wand
from wand.image import Image as wi

# Install tessaract (https://github.com/tesseract-ocr/tesseract/wiki)
# Mac 		- brew install tessaract
#			- pip install pytesseract
# Windows 	- get 4.0.0 from https://github.com/UB-Mannheim/tesseract/wiki
# 			- set the tesseract as ab envitonment variable
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

# Define the directory name contanining the pdf's
# This will default to the current working directory
pdfDirectory = input("What folder name contains the pdf's to scrape? (defaults to the current working directory): ")

# Define the directory the scraped pdf txt files should be saved
# This will default to '/renders'
renderDirectoryName = input("What filder name would you like to store the scraped text? (defaults to 'renders'): ")
renderDirectoryName = renderDirectoryName if renderDirectoryName else 'renders'

# Resolution of the image created from a pdf file
# The files do not interperate hand written or small text at 700 but its fairly quick
# To improve the scraped quality at the loss of scraping speed, increase the resolution by a few hundred
# Files will throw an exception when the render quality is too high ~900
resolution = input("what quality would you like the pdf's to scrape at? (defaults to 700, limit to ~900): ")
resolution = int(resolution) if resolution.isdigit() else 700

# ----------------------------- #
# ---------- Methods ---------- #
# ----------------------------- #

# Saves the given text to a log file and prints it to the console
def log(content, level = 'info'):

	# log with the appropriate level
	if (level is 'info'):
		logger.info(content)
	if (level is 'error'):
		logger.error(content)
	if (level is 'fatal'):
		logger.fatal(content, exc_info = True)

	# print the message to the console
	print(content)

# Returns a string duration of now from a given time
def duration(startTime):
	return str(datetime.now() - startTime)

# Gets a list of pdf file paths in a given directory.
# If no directory is provided, it will default to the current working directory
def getPdfFileNamesFromDirectory(directoryPath): 
	try:
		# if a directory path is given we will use that
		pdfDirectory = os.path.join(workingDirectory, directoryPath) if directoryPath else workingDirectory

		# create a list of pdf files in the file directory if it:
		# - is a valid file
		# - ends with '.pdf'
		return [os.path.join(pdfDirectory, f) for f in listdir(pdfDirectory) if isfile(join(pdfDirectory, f)) if f.endswith('.pdf')]
	except Exception as ex:	
		log(ex, 'fatal')
		sys.exit()

# Returns text from a pdf of a given path.
# The scraped pdf text files will be in a directory called rendered. If the pdf has been rendered the text will be returned
# From that file. If not, the pdf will be scraped, saved and the text returned.
def getFileText(readerFilePath):
	try:
		# Create a directory to store the rendered pdf's in
		renderDirectoryPath = os.path.join(workingDirectory, renderDirectoryName)

		# Create the directory to render files to if it does not exist
		if not os.path.exists(renderDirectoryPath):
			os.makedirs(renderDirectoryPath)

		# Define the name and path of the file we will be creating
		renderFileName = os.path.basename(readerFilePath).split('.')[0] + '.txt'
		renderFilePath = os.path.join(renderDirectoryPath, renderFileName)

		if not os.path.exists(renderFilePath):
			# If the render file exists we will create and write to it
			return scrapePdf(readerFilePath, renderFilePath)
		else:
			# Define the contents of the render file
			renderFile = open(renderFilePath, "r")
			renderFileContents = renderFile.read()

			if not renderFileContents:
				# If the render file exists but is empty, we will write to it
				return scrapePdf(readerFilePath, renderFilePath)
				renderFile.close()
			else:
				# If the render file exists and is populated, we will return its contents
				return renderFileContents
	except Exception as ex: 
		log(ex, 'fatal')
		sys.exit()

# Returns the text from a pdf.
# When the pdf is scraped, the contents will be saved to a given file path.
def scrapePdf(readerFilePath, renderFilePath):
	try:
		log("Beginning scrape of " + readerFilePath)

		# Create and open the file we will add the scraped text to
		with open(renderFilePath,"w+") as renderFile:
			log("Opened render file " + renderFilePath)

			# Open the pdf file to scrape
			with open(readerFilePath, "rb") as file:

				# Define the time we have started processing the pdf
				startTime = datetime.now()
				log("Opened the pdf")

				# Read the pdf file using 'Wand'
				with wi(file = file, resolution = resolution) as source:
					with source.convert('jpeg') as pdfImage:

						log("Converted to jpeg")

						# Define the total number of pages in the pdf for logging
						totalPages = len(pdfImage.sequence)

						# Convert the images to binary strings (blobs)
						imageBlobs = []
						for img in pdfImage.sequence:
							with wi(image = img) as page:
								imageBlobs.append(page.make_blob('jpeg'))
						
						log("Converted pages to blobs")

						completeScrape = ''

						# Loop through all pdf pages with its instance as an image
						for index, blob in enumerate(imageBlobs):
							with Image.open(io.BytesIO(blob)) as im:

								# Add the scraped text
								completeScrape = join(completeScrape, pytesseract.image_to_string(im))

								# Log the progress
								log("Scraped page " + str(index + 1) + " / " + str(totalPages) + " of " + os.path.basename(readerFilePath))

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
startTime = datetime.now()

log("Beginning scrape of " + str(totalPdfs) + " pdf files in '" + pdfDirectory + "'")
log("Outputting redered files to /" + renderDirectoryName)
log("Render resolution set to " + str(resolution))

# For each absolute pdf path in the pdf directory:
for index, readerFilePath in enumerate(pdfPaths):

	# Get the text from the pdf (this will also save the text to a same named file in /renders)
	text = getFileText(readerFilePath)

	log("Complete " + str(index + 1) + " / " + str(totalPdfs) + " total Pdf's")
	log("Current running time is " + duration(startTime))


log("Completed scrape of pdf files in '" + pdfDirectory + "' in " + duration(startTime))

# Terminate the script
sys.exit()











