# Python Text Scraping

A little code snippet to scrape text from pdf's and word documents. The scraping ability comes from googles [tesseract-ocr](https://opensource.google.com/projects/tesseract) which interperates words from an image. 
In this case we convert the desired files to images then let tesseract work its magic.

## Getting Started

These instructions will get you a copy of the project up and running on your local machine.

1. Get python (I use python 3)
2. Get [PIL](https://pillow.readthedocs.io/en/5.1.x/)
	* Mac		- `python3 -m pip install Pillow`
	* Windows	- `python3 -m pip install Pillow`
3.  Get [Wand](http://docs.wand-py.org/en/0.4.4/guide/install.html)
	* Mac		
		* `brew install imagemagick@6` (only v6 works with Wand on mac)
		* `python3 -m pip install Wand`
	* Windows
		* follow [instructions](http://docs.wand-py.org/en/0.4.4/guide/install.html#install-imagemagick-windows)
		* `python3 -m pip install Wand`
4. Get [Tesseract](https://github.com/tesseract-ocr/tesseract/wiki)
	* Mac
		* `brew install tesseract`
		* `python3 -m pip install pytesseract`
	* Windows
		* Install [Tesseract](https://github.com/UB-Mannheim/tesseract/wiki)
	 	* Setup tesseract as an environment variable
		* `python3 -m pip install pytesseract`

## Running

from the directoty of the file simply run `python3 textScraper.py`.
You will be prompted for:
1. The name of the directory where the documents are stored, eg `pdfs`. If nothing is provided, it will look for files in the current working directory.
2. The name of the directory scraped files extractions will be saved. Defaults to `renders`.
3. The resolution of the temporary images 