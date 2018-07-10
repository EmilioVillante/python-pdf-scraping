import logging
from datetime import datetime

# Configures logging to a 'logs.log'
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M',
                    filename='logs.log',
                    filemode='a')

logger = logging.getLogger('logger')


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


# Returns a string duration of now from a given time
def duration(startDuration):
    return str(datetime.now() - startDuration)