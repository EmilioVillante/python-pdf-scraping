import os
from datetime import datetime
from modules import customLogger, dataExtractor, pdfToTxt
import sys

# ------------------------------- #
# ---------- Variables ---------- #
# ------------------------------- #

# Define the current working directory (directory this is run from)
workingDirectory = os.getcwd()

# Define the directory name containing the pdf's
# This will default to the current working directory
pdfDirectory = input("What folder name contains the pdf's to scrape? (defaults to the current working directory): ")

# Define the directory the scraped pdf txt files should be saved
# This will default to '/renders'
renderDirectoryName = input("What folder name would you like to store the scraped text? (defaults to 'renders'): ")
renderDirectoryName = renderDirectoryName if renderDirectoryName else 'renders'

# Resolution of the image created from a pdf file
# The files do not interpret hand written or small text at 700 but its fairly quick
# To improve the scraped quality at the loss of scraping speed, increase the resolution by a few hundred
# Files will throw an exception when the render quality is too high ~900
# Tesseract actually works better with lower quality numbers around 200
resolution = input("what quality would you like the pdf's to scrape at? (defaults to 200, limit to ~600): ")
resolution = int(resolution) if resolution.isdigit() else 200

# ----------------------------- #
# --------- Methods ----------- #
# ----------------------------- #

# ----------------------------- #
# ---------- Script ----------- #
# ----------------------------- #

# Define the absolute path of all pdf's in the given directory
pdfDirectoryPath = os.path.join(workingDirectory, pdfDirectory) if pdfDirectory else workingDirectory
pdfPaths = pdfToTxt.getPdfFileNamesFromDirectory(pdfDirectoryPath)

# Define the total pdf's to scrape for logging
totalPdfs = len(pdfPaths)

# Store the start time of the process for logging
scrapeStart = datetime.now()

customLogger.log("Beginning scrape of " + str(totalPdfs) + " pdf files in '" + pdfDirectory + "'")
customLogger.log("Outputting rendered files to /" + renderDirectoryName)
customLogger.log("Render resolution set to " + str(resolution))

pdfData = {}

# For each absolute pdf path in the pdf directory:
for pdfIndex, path in enumerate(pdfPaths):
    # Get the text from the pdf (this will also save the text to a same named file in /renders)
    extract = pdfToTxt.getFileExtract(path, workingDirectory, renderDirectoryName, resolution)

    customLogger.log("Complete " + str(pdfIndex + 1) + " / " + str(totalPdfs) + " total Pdf's")
    customLogger.log("Current running time is " + customLogger.duration(scrapeStart))

customLogger.log("Completed scrape of pdf files in '" + pdfDirectory + "' in " + customLogger.duration(scrapeStart))

# Terminate the script
sys.exit()
