import logging
import os

logfile = "logs/event.log"
consoleLogging = 1
fileLogging = 1


def putlog(name=__file__, loglevel=logging.DEBUG):
    os.makedirs(os.path.dirname(logfile), exist_ok=True)

    # logger
    logger = logging.getLogger(os.path.basename(name))
    logger.setLevel(loglevel)

    # create formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s:%(lineno)d - %(message)s',
                                  datefmt='%Y-%m-%d %H:%M:%S')

    if consoleLogging == 1:
        ch = logging.StreamHandler()
        ch.setLevel(loglevel)
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    if fileLogging == 1:
        fh = logging.FileHandler(logfile)
        fh.setLevel(loglevel)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    return logger