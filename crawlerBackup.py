# Date: 15/09/20
# Author: Manoj Abhishetty
# Edition: 3

# Structure::
# 1. Setup
# From: https://stackoverflow.com/questions/54372218/how-to-split-a-list-into-sublists-based-on-a-separator-similar-to-str-split
# This is a generator, we can call this multiple times to give the sublists we want.
def list_splitter(list_to_split, delimiter):
    """
    Generator that gives sublists from a list.
    Inputs: list_to_split (list):
            delimiter: where splits should be done. Won't appear in sublists
    Output: sublist
    """
    sublist = []                                    # Set up an empty sublist
    for var in list_to_split:                       # Loop over the list to split
        if var == delimiter:                        # If we have reached the delimiter
            yield sublist                           # Return the sublist as assembled so far
            sublist = []                            # Reset the sublist (I think the next call will start from here, since it is a generator)
        else:                                       # If we are not yet at the delimiter
            sublist.append(var)                     # Add the current element to the sublist
    yield sublist                                   # For the last sublist. Or if there are no delimiters.

def getSiteStatus(req_obj, crawl_instance):
    """
    Function to make sense of the status code from accessing a website.
    Input: requests.response object: contains status code
           crawl_instance: crawler instance, contains URL target
    Output: str_status_code: string containing status code.
    """
    str_status_code = str(req_obj.status_code)
    if len(str_status_code) != 3:
        print('Status code problem, url:', crawl_instance.current_target)
        return str_status_code

    if str_status_code[0] == '2':
        #"Robots acquisition successful. Conditional crawling is likely.")
        return str_status_code

    elif str_status_code[0] == '3':
        print('Redirect, url:', crawl_instance.current_target)
        return str_status_code

    elif str_status_code[0] == '4':
        print("Client error. Assuming no robots file exists, full crawling can proceed, url:", crawl_instance.current_target )
        return str_status_code

    elif str_status_code[0] == '5':
        print('Server error. Assume a temporary error, no crawling shall proceed - url:', crawl_instance.current_target)
        return str_status_code

    else:
        print("Some other error, url:", crawl_instance.current_target)
        return str_status_code

def getAbsUrl(crtVerOfLink, doubleSlashSplitList, rootUrl):
    """
    Function to get the absolute URL provided with some starting URL.
    Inputs: currentVersionOfLink: (str), our current URL string - be it relative/absolute etc.
            doubleSlashSplitList: (list), our list of the Target site URL, split by '//'
            rootUrl: (str), the root url of our target site.
    Output: newLink (str), our absolute URL.
    """
    if crtVerOfLink.startswith('//'):
        newLink = doubleSlashSplitList[0] + crtVerOfLink                        # eg, 'https:' + '//www.google.com'
    elif crtVerOfLink.startswith('/'):                                          # https://www.base.com/new
        newLink = root_url + crtVerOfLink
    elif crtVerOfLink.startswith('http'):
        pass
    else:                                                                       # http://www.base.com/a/b/c/new
        FsingleSlashList_split = doubleSlashSplitList[1].split('/')              #['www.base.com','a','b','c']
        newLink = doubleSlashSplitList[0] + '//' + '/'.join(FsingleSlashList_split[:-1]) + '/' + crtVerOfLink

    return newLink

# pass: mailto addresses.


# 1.2. Class definition

class Crawler():

    def __init__(self, starting_site, num_to_visit, secured, no_goes):
        self.sites_to_visit = [starting_site]                                   # list of sites yet to visit. Starts with seed
        self.current_target = None                                              # Current target site
        self.sites_visited = []                                                 # List of sites that have been visited
        self.num_to_visit = num_to_visit                                        # Total number of sites that should be visited
        self.secured = secured                                                  # True if sites that are NOT secured should be visited
        self.no_goes = no_goes                                                  # List of sites that should NOT be visited
        self.cusHeaders = {'User-Agent':'CustomCrawler(+https://www.mycustomcrawlerexplanations.com)'}          #identifying string passed to server when HTTP request (in header) is made.
        self.sites_dict = {}                                                    # Dictionary that gives sites, with information. Will include all sites the program TRIES to visit.
        self.counter_attempts = 0                                               # Counter to give the current progress of the search.  Gives the number of all sites ATTEMPTED.
        self.counter_total = 0                                                  # Counter to give progress of search. Tracks only sites that have been visited.
        self.crawl_delay = 15                                                   # Number of seconds to wait betweenr requests.

    def robots_check(self):                                                     # Function that examines robots.txt file. Made a function to make code cleaner.
        """
        Function to check whether we are prohibited from visiting a site based on /robots.txt restrictions.
        Inputs: object of class Crawler. Need: current_target, cusHeaders
        Outputs: crawlable (Bool), True if we can crawl. False otherwise.
                 str_status (int), For the dictionary
        """

        # 1. Get root of site url.
        site_pieces = self.current_target.split('//',1)
        second_list = site_pieces[1].split('/',1)
        root_url = site_pieces[0] + '//' + second_list[0]

        # 2. Try to 'get' the robots file. Interpret status_code accordingly
        robots_url = root_url + '/robots.txt'
        robots_req_obj = requests.get(robots_url, headers = self.cusHeaders)

        # 3. To get the extension of the site to visit:
        # tExtension = self.current_target - root_url
        tExtension = '/' + second_list[1]

        # 4. Status codes with string conversion
        str_status = getSiteStatus(robots_req_obj, self)
        if str_status[0] != '2':
            crawlable = False
            return crawlable, int(str_status)

        # 5. Split the text of the robots file up into a list.
        robots_list = robots_req_obj.text.split('\n')

        # 6. CLOSE object now that we are done with it (terminate connxn with server so we don't stress it)
        robots_req_obj.close()

        # 7. This splits our 'robots' list into a number of other lists, all separated by ''. We have a generator iterator.
        generator_robots_list = list_splitter(robots_list,'')

        # 8. Extract rules from each sublist

        # Documentation: We iterate over each 'record' (defined between empty lines)
            # We get a 'list' for each of these. We iterate over each element in the list (split by newlines)
            # We strip any spaces/'.'
            # If the line starts with a '#', we add the content to a comment string.
            # If the line starts with user and ends with '*'

        final_dict = {}
        for sublist in list_splitter(robots_list, ''):
            # We are only interested in the User-Agent '*' or 'CustomCrawler(+https://www.mycustomcrawlerexplanations.com)'
            # I'll look for comments in each of the sublists
            comment_string = ''
            flag = 0
            for element in sublist:
                flag += 1
                stripped_el = element.strip(' .')                               # strings aren't mutable! Removing spaces and '.'s because of the search that comes next.
                if stripped_el.startswith('#'):
                    comment_string += stripped_el                               # Making a string of all comments.

                # if the entry is a user-agent and corresponds to all crawlers, we are interested in recording the entry.
                elif (stripped_el.startswith('user') and stripped_el.endswith('*')) or (stripped_el.startswith('User') and stripped_el.endswith('*')):
                    pass
                    dict_title = 0
                    # The structure of the sublist is: ['UA: smth, UA: smth_else, Allow: smth, Allow: smth, Disallow: smth_else']
                    # We iterate over the remaining elements of that sublist and add entries to a dictionary. The prior elements in the sublist
                    # don't interest us because they will only be irrelevant UA strings. There is a chance we include irrelevant UA strings in final_dict
                    # if multiple UA's are referred to and UA: * came first. We will deal with this later.
                    for k in range(flag + 1, len(sublist) + 1):
                        element = sublist[k-1]
                        element = element.strip(' .')

                        if element.startswith('#'):
                            continue

                        elif stripped_el.startswith('crawl') or stripped_el.startswith('Crawl'):
                            delayEntry = stripped_el.split(':')
                            self.crawl_delay = int(delayEntry[1].strip(' .'))           # Get the seconds, remove spaces and '.'s, and make it an integer.

                        entry = element.split(':')
                        dict_title += 1
                                                              # pass: won't wprk if there are comments remaining.
                        final_dict.update({dict_title:{'command':entry[0],
                                                       'target':entry[1]}})
                    break                                       # pass: issue potentially with comments in the rest of that sublist

                    # This above code assumes that UA: * only occurs once in a robots file. I think that this is a reasonable assumption.
        # Comments in the /robots.txt file
        print('These are the comments from the .robots.txt file:', comment_string)
        shallWeContinue = input('Based on the comments from the robots file, do you wish to continue?(Y/N): ')
        if 'N' in shallWeContinue:
            crawlable = False
            return crawlable, int(str_status)

        disallow_list = []
        allow_list = []
        #9. Now we need to make sure that the entries are all 'allow' or 'disallow' commands and get the info
        for i in range(1, len(final_dict) + 1):
            # If 'allow' or 'disallow' are not in the first entry (we probably have a comment or UA string)
            # Check disallow first, since 'disallow' also has the string 'allow' in it.
            if ('disallow' in (final_dict.get(i)).get('command')) or ('Disallow' in (final_dict.get(i)).get('command')):
                disallow_list.append((final_dict.get(i)).get('target'))

            # only executed if disallow not present. Don't worry about duplicates (?)
            elif ('allow' in (final_dict.get(i)).get('command')) or ('Allow' in (final_dict.get(i)).get('command')):
                allow_list.append((final_dict.get(i)).get('target'))

            # get rid of comment/UA entries.
            else:
                final_dict.pop(i)

        # 9.2 RegExps
        # el is part of a URL. We need to do 'root_url' + el (pass)
        allow_list_regex = []
        disallow_list_regex = []

        for ii in range(1,3):
            if ii == 1:
                list_r = disallow_list
            else:
                list_r = allow_list

            # entries in this list are just relative paths that will be allowed/disallowed.
            for el in list_r:
                # Strip whitespace
                el = el.strip(' ')
                # Replace and remove certain characters: ends with '*' or '?' -> remove
                wEndswithSafety = 0
                while el.endswith('*') or el.endswith('?'):
                    el = el[:-1]
                    wEndswithSafety += 1                                        # Preventing infinite loops
                    if wEndswithSafety >= 500:
                        break

                # First check for any special characters - protect them: '.', '?', '$', '*'
                    # What we are trying to do is change targets, such as: /food/recipes* into a 'regular expression'.
                    # Then we will check to see if our URL matches with the RegExps.
                    # The reason we protect is because these characters have special RegEx meanings that we don't want them to take on here.
                                                                                            # going to remove 'if' statements, won't do anything if string_to_replace isn't present.
                el = el.replace('.', r'\.')
                el = el.replace('?', r'\?')
                if '$' in el:
                    if '$' != el[-1]:                                           # If '$' is the last character, we don't want to replace it. It has some meaning.
                        el = el.replace('$', r'\$')
                el = el.replace('[', r'\[')
                el = el.replace(']', r'\]')

                el = el.replace('(', r'\(')
                el = el.replace(')', r'\)')


                # Then replace any '*' with '.*'. This is for the RegExp. This allows us to match the command '*', which means any string.
                # Important that we do this AFTER protections. Otherwise the '.' gets protected and loses the RegEx meaning - which we want in this case.
                el = el.replace('*', '.*')

                # Then add '^' at the start
                el = '^' + el

                if ii == 1:
                    disallow_list_regex.append(el)
                else:
                    allow_list_regex.append(el)

        # 10. Check the URL against each of the rules. If it passes the test, continue. Otherwise, add it to the dictionary and explain the ROBOTS issue.
        # We'll have to check both lists. For example, you might disallow all but allow a few sites. So we need to check for that.
        # First check for exceptional circumstances. These are the: ' ' and '/' entries.
        # According to: http://www.robotstxt.org/robotstxt.html, 'everything not explicitly disallowed is considered fair game'
        crawlable = True                                                        # F: Prohibited, T: allowed

        for el in disallow_list_regex:
            # A statement: 'Disallow: ' -> '^'. Disallowing nothing
            if el == '^':
                pass
            # A statement: 'Disallow: /' -> '^/'. Disallowing everything
            elif el == '^/':
                crawlable = False
            else:
                x = re.search(el, tExtension)
                # If there is a match - our target url appears in disallow
                if x:
                    crawlable = False

        if crawlable == False:                                               # Now we have been prohibited, lets check allow list
            for el in allow_list_regex:
                # A statement: 'Allow: ' -> '^'. Allow nothing
                if el == '^':
                    pass                                                        # Since we are currently prohibited, and nothing is allowed
                # A statement: 'Allow: /' -> '^/'. Allow everything.
                # From: 'https://developers.google.com/search/reference/robots_txt', In case of conflicting rules, including those with wildcards, the least restrictive rule is used.
                elif el == '^/':
                    crawlable = True
                else:
                    x = re.search(el, tExtension)
                    if x:
                        crawlable = True
        return crawlable, int(str_status)                                       # True: allowed, False: prohibited

    def ToS_check(self):                                                        # Function that examines the terms of service. Sees if we can crawl
        """
        Function to check the Terms of Service on the webpage.
        Check both the root site and the ToS page, if they can be found.
        Inputs: crawler instance.
        Outputs: okContinue (Y/N) (str): can the crawl progress or are we prohibited?
                 ToS_status (int): status code of request [either for the Homepage or T&C's page]
        """
        # 1. Get root of site url.
        site_pieces = self.current_target.split('//',1)                         # ['https:','www.abcd.com....etc']
        second_list = site_pieces[1].split('/',1)                               # ['www.abcd.com','a','b','c']
        root_url = site_pieces[0] + '//' + second_list[0]                       # 'https://www.abcd.com'

        # Having just visited the robots page, we shall wait a certain amount of time before moving forward.
        time.sleep(self.crawl_delay)
        # 2. Visit root site
        root_req_obj = requests.get(root_url, headers = custom_headers)
        root_status = getSiteStatus(root_req_obj)
        if root_status[0] != '2':
            okContinue = 'N'
            print("Problem establishing connxn with Homepage")
            return okContinue, int(root_status)
            # Search homepage for links
        homepage_soup = BeautifulSoup(root_req_obj.text, 'lxml')
        # CLOSE connxn so that we don't stress server.
        root_req_obj.close()

        # Search all the links on the homepage for any mention of 'terms'
        # If such a link is found, store the link (pass: multiple 'terms' links.)
        ToS_link = ''
        for link in homepage_soup.find_all('a'):
            try:
                if 'terms' in link.string or 'Terms' in link.string:
                    ToS_link = link.get('href')
            except TypeError:
                pass

        ####
        # 5.2. Head to the 'terms' page and search for 'robots'/'crawler'/'spider'
        if (ToS_link != '') and (ToS_link != None) and (not ToS_link.startswith('#')):                                 # Some URLs are relative!!! we need to sort these out 'pass:'
            ToS_link_full = getAbsUrl(ToS_link, site_pieces, root_url)
            # Wait again:
            time.sleep(self.crawl_delay)
            #####
            terms_req_obj = requests.get(ToS_link_full, headers = custom_headers)
            tos_status = getSiteStatus(terms_req_obj)
            if tos_status[0] != 2:
                okContinue = 'N'
                print("Problem establishing connxn with ToS page")
                return okContinue, int(tos_status)

            listOf_TandCs = (terms_req_obj.text).split('\n')
            # CLOSE connxn now that we are done with it - so that we dont stress the server
            terms_req_obj.close()

            for sublist_TandCs in list_splitter(listOf_TandCs,''):
                if ('robot' in sublist_TandCs) or ('Robots' in sublist_TandCs) or ('crawler' in sublist_TandCs) or ('Crawler' in sublist_TandCs) or ('spider' in sublist_TandCs) or ('Spider' in sublist_TandCs):
                    # 5.3. Show the user the 'terms'. If they read it and wish to continue, they may do so. Otherwise not.
                    print(sublist_TandCs)
            okContinue = input("Based on the above, will you continue with the crawl? Do the T&C's allow it? (Y/N) ")

        else:                                                                   # If we can't find a ToS easily, assume we go ahead with the crawl.
            okContinue = 'Y'

        return okContinue, int(tos_status)

#-0-0--0-0-0-0-0-0-0-0-0-0-0-0-0-0-0-0-0-0-0-0-0--0-0-0-0-0-0--0-0-0-0-0-0-0-0-0-0-0
#-0-0--0-0-0-0-0-0-0-0-0-0-0-0-0-0-0-0-0-0-0-0-0--0-0-0-0-0-0--0-0-0-0-0-0-0-0-0-0-0
# Format for sites_dict:
# {'url':(string),              - The url of this site, in string form.
# 'links':(NoneType),           - The links from this site. Will be a list of strings.
# 'status':(NoneType),          - The HTTP status code, 2xx, 3xx, 4xx, 5xx etc. Integers
# 'redirect':(NoneType),        - Whether or not we have been redirected. Bool, True if redirected
# 'duration':(NoneType),        - Returns a float with the time, in seconds, elapsed between making and receiving request contents.
# 'robots':(Bool),              - Are we prohibited from crawling due to the /robots.txt file? True if prohibited
# 'ToS':(Bool),                 - Are we prohibited from crawling due to the ToS? True if prohibited
# 'Repeat':(Bool),              - Is this site a repeat of a previous one? True if so
# 'no-go':(Bool)}               - Is this a no-go site? True if so.
#-0-0--0-0-0-0-0-0-0-0-0-0-0-0-0-0-0-0-0-0-0-0-0--0-0-0-0-0-0--0-0-0-0-0-0-0-0-0-0-0
#-0-0--0-0-0-0-0-0-0-0-0-0-0-0-0-0-0-0-0-0-0-0-0--0-0-0-0-0-0--0-0-0-0-0-0-0-0-0-0-0

# 1.1. Import modules
import re
import requests
from bs4 import BeautifulSoup
from sys import exit
import time

# 1.3. Ask user for inputs and check if they are appropriate.
print("""\
This script aims to crawl a small portion of the web to develop a network representation.
This is so that mathematical techniques can be used to analyse network structure.
You now need to give some inputs: """)
# 1.3.1. Ask for seed site, sites you want to avoid, https issues, how many to visit,
start_site = input("Type the website you wish to start from: ")
avoid_sites = input("Are there any sites you wish to avoid? Type them here, separated by a pipe (|). All sites in those domains won't be visited, so just type in the root and all sites beneath it will be avoided: ")
steps = input("How many sites would you like to visit. These are the sites we will actually go to: ")
secured = input("Enter 'True' if you would like to include sites that are not secured (http). Enter 'False' if not: ")

# 1.4. Allocate memory
custom_headers = {'User-Agent':'CustomCrawler(+https://www.mycustomcrawlerexplanations.com)'}
# 1.4.1. Store all from inputs
try:
    start_site_string = str(start_site)
except:
    exit("Error while handling starting website string")

try:
    steps_number = int(steps)
except ValueError:
    exit("Error while handling the number of steps. Please enter an integer")
except:
    exit("Error while handling the number of steps.")

#3.1: 2.3
if 'True' in secured:
    secured_bool = True
else:
    secured_bool = False

try:
    no_go_list = avoid_sites.split('|')
except:
    exit("Error when splitting the 'no-go' sites")

# Create object
myCrawler = Crawler(start_site_string, steps_number, secured_bool, no_go_list)

###------------------------------- LOOP START -------------------------------###

wMainLoopSafety = 0
while len(myCrawler.sites_visited) < myCrawler.num_to_visit:
# Reset the delay
    myCrawler.crawl_delay = 15
# 2. Take a starting website
    try:
        myCrawler.current_target = myCrawler.sites_to_visit.pop(0)
    except IndexError:
        exit("Finished.")
# 3. Check if we WANT to visit it. (if not, we can record it as an ending stub in the diagram)
    # What shall we exclude? (1) Sites we just don't want to visit, (2) 'mailto' or 'ftp' schemes, (3) None sites or (4) # sites (seen on https://www.riotgames.com, for example.)
    skip = False
    for preventIterator in range(0, len(myCrawler.no_goes) + 1):                # All elements in a list
        if myCrawler.current_target.startswith(myCrawler.no_goes[preventIterator]):
            skip = True


    if skip or 'mailto' in myCrawler.current_target or 'ftp' in myCrawler or myCrawler.current_target is None or myCrawler.current_target.startswith('#'):
        myCrawler.counter_attempts += 1
        myCrawler.sites_dict.update({myCrawler.counter_attempts:{'url':myCrawler.current_target,
                                                                 'links':None,
                                                                 'status':None,
                                                                 'redirect':None,
                                                                 'duration':None,
                                                                 'robots':False,
                                                                 'ToS':False,
                                                                 'Repeat':False,
                                                                 'nogo':True}})
        # Skip the rest of this code and move onto the next iteration of the loop.
        continue

# 3.5. Check if we have already visited it:
    if myCrawler.current_target in myCrawler.sites_visited:
        myCrawler.counter_attempts += 1
        myCrawler.sites_dict.update({myCrawler.counter_attempts:{'url':myCrawler.current_target,
                                                                 'links':None,
                                                                 'status':None,
                                                                 'redirect':None,
                                                                 'duration':None,
                                                                 'robots':False,
                                                                 'ToS':False,
                                                                 'Repeat':True,
                                                                 'nogo':False}})
        # Skip the rest of this code and move onto the next iteration of the loop.
        continue

# 4. Check if we are PERMITTED to visit it (robots file)
    # Returns a bool TRUE if we can crawl
     m_crawlable, robot_status = myCrawler.robots_check()
     if not m_crawlable:
        myCrawler.counter_attempts += 1
        myCrawler.sites_dict.update({myCrawler.counter_attempts:{'url':myCrawler.current_target,
                                                                 'links':None,
                                                                 'status':None,
                                                                 'redirect':None,
                                                                 'duration':None,
                                                                 'robots':True,
                                                                 'ToS':False,
                                                                 'Repeat':False,
                                                                 'nogo':False}})
        # Skip the rest of this code and move onto the next iteration of the loop.
        continue

# 5. Check if the TERMS allow us to access the desired site
    # Since we are not completely probited from crawling, it stands to reason that we can visit the Homepage -> T&C's to check
    # Homepage
# 5.1. Go to the homepage and search for links to a 'terms'/'service'/'use' site.

    ToS_outcome, tos_code = myCrawler.ToS_check()
# 5.3. Are we going ahead?
    if ToS_outcome != 'Y':
        # The code for being blocked by the ToS
        myCrawler.counter_attempts += 1
        myCrawler.sites_dict.update({myCrawler.counter_attempts:{'url':myCrawler.current_target,
                                                                 'links':None,
                                                                 'status':None,
                                                                 'redirect':None,
                                                                 'duration':None,
                                                                 'robots':False,
                                                                 'ToS':True,
                                                                 'Repeat':False,
                                                                 'nogo':False}})
         # Skip the rest of this code and move onto the next iteration of the loop.
         continue

    # 6. Visit the desired site and extract content
    # 6.1. Requests module. Don't forget to pass custom UA string
    main_link_list = []
    # Wait again:
    time.sleep(myCrawler.crawl_delay)
    ###
    main_siteContentStuff = requests.get(current_target, headers = custom_headers)
    main_code = getSiteStatus(main_siteContentStuff)
    if main_code[0] != '2':
        myCrawler.counter_attempts += 1
        myCrawler.sites_dict.update({myCrawler.counter_attempts:{'url':myCrawler.current_target,
                                                                 'links':None,
                                                                 'status':int(main_code),
                                                                 'redirect':None,
                                                                 'duration':None,
                                                                 'robots':False,
                                                                 'ToS':False,
                                                                 'Repeat':False,
                                                                 'nogo':False}})
        continue

    main_soup = BeautifulSoup(main_siteContentStuff.text, 'lxml')


    # 6.2. Get Links
    # Get root url
    url_split_list = myCrawler.current_target.split('//',1)                     # Should give smth like ['https:','www.abcd.com/1/2/3/4...']
    domain_split_list = url_split_list[1].split('/',1)                          # Should give smth like ['www.abcd.com','1/2/3/4...']
    root_url = url_split_list[0] + '//' + domain_split_list[0]                  # Gives 'https://www.abcd.com'
    # Slightly more to this than just adding links. We'll check for the starting characters, to see if the relative URLs need to be extended to absolute
    for main_link in main_soup.find_all('a'):
        link_to_add = main_link('href')                                     # Since links have lots of things going on, incl. classes etc.
        link_to_add_NOW = getAbsUrl(link_to_add, url_split_list, root_url)
        main_link_list.append(link_to_add_NOW)
    # Now every link that is added will have a full, absolute web address.

    # 6.3. Store the information:
    myCrawler.counter_attempts += 1
    myCrawler.sites_dict.update({myCrawler.counter_attempts:{'url':myCrawler.current_target,
                                                             'links':main_link_list,
                                                             'status':main_siteContentStuff.status_code,
                                                             'redirect':main_siteContentStuff.is_redirect,
                                                             'duration':(main_siteContentStuff.elapsed).total_seconds,
                                                             'robots':False,
                                                             'ToS':False,
                                                             'Repeat':False,
                                                             'nogo':False}})

# 7. Close connection with site (done for each as soon as we are done with the command - so that connxn is open for minimum time)
    # CLOSE connxn now that we are done with it - so as not to stress the server
    main_siteContentStuff.close()                                               # pass close or close()
# 8. Read the content into HTML links.
# 9. Check that the links are all good (traps, format etc)
# 10. Add the links into a store and the name of the visited site
    myCrawler.sites_to_visit.extend(main_link_list)
    myCrawler.sites_visited.append(myCrawler.current_target)
# 11. Delete any excess content
# 12. Repeat this process, checking whether or not we have already visited that particular site.
# Wait again - otherwise there might not be sufficient time between a request to the TARGET and to the next robots page
    time.sleep(myCrawler.crawl_delay)
####
    del main_link_list, main_siteContentStuff, main_soup
    wMainLoopSafety += 1
    if wMainLoopSafety >= 1000:
        break

###------------------------------- LOOP END -------------------------------###
# 11. Delete any excess content
