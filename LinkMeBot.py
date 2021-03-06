"""
/u/PlayStoreLinks__Bot

A Reddit Bot made by /u/cris9696 

General workflow:

* login
* get comments
* analyze comments
* reply to valid comments
* shutdown


"""

#reddit
import praw
#general
import sys
import time
import os
import re
import pickle
#web
import urllib
import html
#mine
import Config
import PlayStore

def stopBot():
    logger.info("Shutting down")
    if os.path.isfile(Config.botRunningFile):
        logger.debug("Deleting lock file")
        os.remove(Config.botRunningFile)

    sys.exit(0)

def removeRedditFormatting(text):
    return text.replace("*", "").replace("~", "").replace("^", "").replace(">","").replace("[","").replace("]","").replace("(","").replace(")","")


def isDone(comment):
    #TODO check if in the database
    comment.refresh()
    for reply in comment.replies:
        if reply.author.name.lower() == Config.username.lower():
            logging.debug("Already replied to \"" + comment.id + "\"")
            return True

    return False

def generateReply(link_me_requests):
    my_reply = ""

    nOfRequestedApps = 0
    nOfFoundApps = 0
    for link_me_request in link_me_requests:    #for each linkme command
        requested_apps = link_me_request.split(",") #split the apps by ,

        for app_name in requested_apps:
            app_name = app_name.strip()

            if len(app_name) > 0:
                app_name = html.unescape(app_name)  #html encoding to normal encoding 
                nOfRequestedApps += 1
                
                if nOfRequestedApps <= Config.maxAppsPerComment:
                    app = findApp(app_name)

                    if app:
                        if len(requested_apps) == 1 and len(link_me_requests) == 1: #build pretty reply
                            my_reply += "[**" + app.name + "**](" + app.link + ") by " + app.author + " | "
                            my_reply += (" Free " if app.free else ("Paid: " + app.price)) + " "
                            my_reply += ("with IAP" if app.IAP else "") + "\n\n"
                            my_reply += "Description: " + app.description + "\n\n"
                            my_reply += "Average rating of " + app.rating + "/100 | "
                            my_reply += app.num_downloads + " downloads.\n\n"
                            my_reply += "Search for '" + app_name + "' on the [**Play Store**](https://play.google.com/store/search?q=" + urllib.parse.quote_plus(app_name) + ")\n\n"
                        else:
                            my_reply += "[**" + app.name + "**](" + app.link + ") - "
                            my_reply += ("Free " if app.free else ("Paid: " + app.price)) + " "
                            my_reply += ("with IAP - " if app.IAP else " - ") 
                            #my_reply += ("Ad-supported - " if app.IAP else "") 
                            my_reply += "Rating: " + app.rating + "/100 - "
                            my_reply += "Search for '" + app_name + "' on the [**Play Store**](https://play.google.com/store/search?q=" + urllib.parse.quote_plus(app_name) + ")\n\n"
                        
                        nOfFoundApps += 1
                        logger.info("'" + app_name + "' found. Name: " + app.name)
                    else:
                        my_reply +="I am sorry, I can't find any app named '" + app_name + "'.\n\n"
                        logger.info("Can't find any app named '" + app_name + "'")

    if nOfRequestedApps > Config.maxAppsPerComment:
        my_reply = "You requested more than " + str(Config.maxAppsPerComment) + " apps. I will only link to the first " + str(Config.maxAppsPerComment) + " apps.\n\n" + my_reply
    
    my_reply += Config.closingFormula

    if nOfFoundApps == 0:   #return None because we don't want to answer
        my_reply = None

    return my_reply


def findApp(app_name):
    logger.debug("Searching for '" + app_name + "'")
    app_name = app_name.lower()
    app = None

    if len(app_name)>0:
        #app = searchInDatabase(app_name)
        #if app:
        #     return app
        # else:
        try:
            playstoreclient = PlayStore.PlayStoreClient(logger_name=Config.loggerName)
            app = playstoreclient.search(app_name)
            return app
        except PlayStore.AppNotFoundException as e:
            return None 
    else:
        return None

def doReply(comment,myReply):
    logger.debug("Replying to '" + comment.id + "'")
    
    tryAgain = True
    while tryAgain:
        tryAgain = False
        try:
            # "#&#009;\n\n###&#009;\n\n#####&#009;\n"
            comment.reply(myReply)
            logger.info("Successfully replied to comment '" + comment.id + "'\n")
            break
        except praw.errors.RateLimitExceeded as timeError:
            logger.warning("Doing too much, sleeping for " + str(timeError.sleep_time))
            time.sleep(timeError.sleep_time)
            tryAgain = True
        except Exception as e:
            logger.error("Exception '" + str(e) + "' occured while replying to '" + comment.id + "'!")
            stopBot()


#building the logger
import logging
logger = logging.getLogger(Config.loggerName)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
fh = logging.FileHandler(Config.logFile)
fh.setLevel(Config.loggingLevel)
fh.setFormatter(formatter)
ch = logging.StreamHandler()
ch.setFormatter(formatter)
logger.addHandler(fh)
logger.addHandler(ch)

#main method
if __name__ == "__main__":

    logger.info("Starting up")

    if os.path.isfile(Config.botRunningFile):
        logger.warning("Bot is already running!")
        stopBot()
    else:
        with open(Config.botRunningFile, 'a'):
            pass

    logger.debug("Logging in")


    try:
        r = praw.Reddit("/u/PlayStoreLinks__Bot by /u/cris9696 V3.0")
        r.login(Config.username, Config.password, disable_warning=True)
        logger.info("Successfully logged in")

    except praw.errors.RateLimitExceeded as error:
        logger.error("The Bot is doing too much! Sleeping for " + str(error.sleep_time) + " and then shutting down!")
        time.sleep(error.sleep_time)
        stopBot()

    except Exception as e:
        logger.error("Exception '" + str(e) + "' occured on login!")
        stopBot()


    subreddits = r.get_subreddit("+".join(Config.subreddits))

    link_me_regex = re.compile("\\blink[\s]*medebug[\s]*:[\s]*(.*?)(?:\.|;|$)", re.M | re.I)

    try:
        logger.debug("Getting the comments")
        comments = subreddits.get_comments()
        logger.info("Comments successfully downloaded")
    except Exception as e:
        logger.error("Exception '" + str(e) + "' occured while getting comments!")
        stopBot()

    for comment in comments:
        #to avoid injection of stuff
        clean_comment = removeRedditFormatting(comment.body)

        #match the request
        link_me_requests = link_me_regex.findall(clean_comment)
        #if it matches
        if len(link_me_requests) > 0:
            if not isDone(comment): #we check if we have not already answered to the comment
                logger.debug("Generating reply to '" + comment.id + "'")
                reply = generateReply(link_me_requests)
                if reply is not None:
                    doReply(comment,reply)
                else:
                    logger.info("No Apps found for comment '" + comment.id + "'. Ignoring reply.")
    stopBot()
