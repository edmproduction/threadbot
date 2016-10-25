import requests, sys, pprint, datetime
from optparse import OptionParser
import ConfigParser

reddit_url = "https://www.reddit.com/"
debug_printer = pprint.PrettyPrinter()  # for debugging
config = ConfigParser.RawConfigParser()
session = requests.Session()


def read_config():
    """
    Reads config file from program arguments
    """
    parser = OptionParser()
    parser.add_option("-c", "--config", dest="conf_path", type="string", help="config file path")
    (options, args) = parser.parse_args()

    config.readfp(open(options.conf_path))  # "threadbot.cfg"
    subreddit = config.get("threadbot", "subreddit")
    username = config.get("threadbot", "username")
    password = config.get("threadbot", "password")

    return subreddit, username, password


def login():
    """
    Logs the user in
    """
    user_pass_dict = {'user': username,
                      'passwd': password,
                      'api_type': 'json'}

    r = session.post('https://www.reddit.com/api/login', data=user_pass_dict)
    login = r.json()['json']['data']
    cookie = {'cookie': login['cookie']}
    modhash = login['modhash']

    return cookie, modhash


def get_weekday():
    """
    Gets the current weekday
    """
    try:
        day = config.getint("threadbot", "debug_day")
    except ConfigParser.NoOptionError:
        d = datetime.date.today()
        day = d.weekday()
    sort_by_new = False

    # 0 / Monday / Feedback thread
    # 1 / Tuesday / How do I make this sound thread
    # 2 / Wednesday / There are no stupid questions thread
    # 3 / Thursday / Marketplace thread
    dayname = "waffles"
    if day == 0:
        dayname = "monday"
        sort_by_new = True
    elif day == 1:
        dayname = "tuesday"
        sort_by_new = True
    elif day == 2:
        dayname = "wednesday"
        sort_by_new = True
    elif day == 3:
        dayname = "thursday"
        sort_by_new = False
    else:
        sys.exit(1)  # woo inelegance

    return dayname, sort_by_new


def get_thread(dayname):
    """
    Gets the current day's thread
    """
    d = datetime.date.today()

    try:
        title = config.get(dayname, "title") + ' (' + d.strftime("%B %d") + ')'
        text = config.get(dayname, "text")
    except:
        sys.exit(2)  # nothing found for today
    text = "\n\n".join(text.split("\n"))

    return title, text


def handle_captcha(thread_call, thread_r):
    """Makes a user input the answer to a capatcha if there is one"""
    import subprocess

    iden = thread_r['captcha']

    subprocess.call(['open', reddit_url + 'captcha/' + iden])
    thread_call['captcha'] = input("Captcha (enclose in quotes):")
    thread_call['iden'] = iden

    request = session.post(reddit_url + 'api/submit', data=thread_call, cookies=cookie)
    thread_r = request.json()['json']['data']
    print request.json()
    if len(thread_r['errors']) > 0:
        debug_printer.pprint(thread_r)


def post_thread():
    """
    Posts the thread, duh
    """
    thread_call = {'api_type': 'json',
                   'kind': 'self',
                   'sr': subreddit, 'uh': modhash,
                   'title': title,
                   'text': text}

    request = session.post(reddit_url + 'api/submit', data=thread_call, cookies=cookie)

    thread_r = request.json()['json']
    if len(thread_r['errors']) > 0:
        print "fuckin captcha or something"
        handle_captcha(thread_call, thread_r)

    thread_r = thread_r['data']
    name = thread_r['name']
    url = thread_r['url']

    return name, url


def distinguish(modhash, cookie, name):
    """
    Make the poster have a mod flair
    """
    dist_data = {'api_type': 'json', 'how': 'yes', 'id': name, 'uh': modhash}
    request = session.post(reddit_url + 'api/distinguish', data=dist_data, cookies=cookie)

    thread_r = request.json()['json']
    if len(thread_r['errors']) > 0:
        debug_printer.pprint(thread_r)


def contest_mode(modhash, cookie, name):
    """
    Puts the thread in contest mode (aka, randomly sorted posts without scores)
    """
    dist_data = {'api_type': 'json', 'id': name, 'state': 'true', 'uh': modhash}
    request = session.post(reddit_url + 'api/set_contest_mode', data=dist_data, cookies=cookie)

    thread_r = request.json()['json']
    if len(thread_r['errors']) > 0:
        debug_printer.pprint(thread_r)


def beg_to_sort(modhash, cookie, text, name, url):
    """
    Edits the thread to include a link to itself, but sorted by new
    """
    url += '?sort=new'
    body_text = "**[Please sort this thread by new!](" + url + ")**\n\n " + text
    edit_data = {'api_type': 'json', 'text': body_text, 'thing_id': name, 'uh': modhash}
    request = session.post(reddit_url + 'api/editusertext', data=edit_data, cookies=cookie)


if __name__ == "__main__":
    # Set the session header
    session.headers.update({'User-Agent': 'edmproduction weekly threadbot by /u/fiyarburst'})

    # Get basic info from the config
    subreddit, username, password = read_config()

    # Login
    cookie, modhash = login()

    # Select today's thread
    dayname, sort_by_new = get_weekday()
    title, text = get_thread(dayname)

    # Post the thread
    name, url = post_thread()

    # Mod-Distinguish thread
    distinguish(modhash, cookie, name)

    # Put thread in contest mode
    contest_mode(modhash, cookie, name)

    # Edit to include "sort by new" link
    if sort_by_new:
        beg_to_sort(modhash, cookie, text, name, url)

    print url
