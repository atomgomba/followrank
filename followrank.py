from sys import exit
from math import ceil
from os.path import exists
import pickle
from hashlib import md5
import optparse

try:
    import soundcloud
except ImportError:
    exit("* Please install SoundCloud SDK for Python!")


CLIENT_ID = "7c60921f5c70d104f9586f40149f02f2"

"""
From the SoundCloud API docs:

    "The maximum value is 200 for limit and 8000 for offset."
    http://developers.soundcloud.com/docs#pagination
    
It means that it's impossible to retrieve more than 8200 followers.
"""
API_LIMIT = 8200

    
def get_user_info(username):
    """Retrieves basic information about a user by name.
    """
    global client
    print "Querying user '%s'..." % username
    res = client.get("/resolve",
                     url="http://soundcloud.com/%s" % username,
                     limit=1)

    # verify received data
    userinfo = None
    try:
        if res.kind == "user":
            userinfo = { "id"               : int(res.id),
                         "username"         : res.username,
                         "followers_count"  : float(res.followers_count) }
        else:
            raise AttributeError
    except AttributeError:
        # data is incomplete or not a user
        exit("* No data found. Please try another username!")
        
    print "\tuser id: %(id)d\n\tfollowers count: %(followers_count)d" % userinfo
    return userinfo


def get_followers(user_id, max_followers, page_size):
    """Retrieves the followers of a user by id.
    """
    global client
    print "Retrieving followers (%d)..." % max_followers
    ret = {}
    page = 0
    offset = 0
    max_pages = ceil(float(max_followers) / float(page_size))
    url = "/users/%d/followers" % user_id
    
    try:
        while page < max_pages:
            perc = round(100.0 * (float(page+1) / max_pages), 2)
            print "\t", "downloading from offset %d (%.2f%%)" % (offset, perc)

            reslist = client.get(url,
                                 offset=offset,
                                 limit=page_size)
            if len(reslist) == 0:
                break
            for res in reslist:
                ret[res.id] = {
                    "id"                : int(res.id),
                    "username"          : res.username,
                    "followers_count"   : float(res.followers_count),
                    "followings_count"  : float(res.followings_count)}

            page += 1
            offset = page * page_size
            if (max_followers - offset) < page_size:
                page_size = int(max_followers - offset)
            
    except AttributeError:
        # this shall never happen
        exit("* Invalid data from server!")
    except:
        exit("* Download interrupted. Exiting.")

    print "\t", "total count: %d" % len(ret.values())
    return ret
    

def download(options, args):
    """Downloads all the information required for the calculation.
    """
    username = args[0]
    cachefile = "%s.pickle" % md5(username).hexdigest()
    if options.caching:
        if exists(cachefile):
            print "Loading user data from file: %s" % cachefile
            return pickle.load(file(cachefile, "r"))
    
    # force API limit
    if API_LIMIT < options.max_followers:
        options.max_followers = API_LIMIT
    # limit page size
    if 200 < options.page_size:
        options.page_size = 200
    # adjust page size
    if options.max_followers < options.page_size:
        options.page_size = options.max_followers
        
    global client
    client = soundcloud.Client(client_id=CLIENT_ID)   

    # get basic information about user
    info = get_user_info(username)

    # limit the number of items to retrieve
    if options.max_followers < info["followers_count"]:
        info["followers_count"] = options.max_followers

    # get followers' information
    followers = get_followers(info["id"],
                              info["followers_count"],
                              options.page_size)
    
    ret = { "info" : info, "followers" : followers }
    if options.caching:
        pickle.dump(ret, file(cachefile, "w+"))
        
    return ret
    

def calculate_score(data):
    """Calculates follower ranking based on input data.
    """
    # compute follower/following ratio
    score = 0
    for key in data["followers"]:
        follower = data["followers"][key]
        score += follower["followers_count"] / follower["followings_count"]
    return score


def main():
    print "SoundCloud Follower Ranking", "\n", "---"
    
    parser = optparse.OptionParser("Usage: %prog [options] username")
    parser.add_option("-l", "--limit", dest="page_size",
                      default=200, type="int",
                      help="Number of items per result set (max. 200)")
    parser.add_option("-m", "--max_followers", dest="max_followers",
                      default=API_LIMIT, type="int",
                      help="Maximum number of followers to retrieve (max. %d)" % API_LIMIT)
    parser.add_option("-n", "--no-cache", dest="caching",
                      default=True, action="store_false",
                      help="Disable caching")
    
    options, args = parser.parse_args()
    if len(args) != 1:
        parser.error("Please specify a username!")

    data = download(options, args)
    score = calculate_score(data)

    print "User score: %d" % score
    

client = None

if __name__ == "__main__":
    main()
