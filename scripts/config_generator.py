#!/usr/bin/env python

# if you pas

import sys
import os
import os.path
import pwd

try:
    import readline
except ImportError:
    pass

def ask(question, default=None, compulsory=False, restrict=None):
    print
    
    def do_ask(to_ask, default):
        answer = raw_input(to_ask)
        if answer == '' and default != None:
            return default
        elif answer == '':
            return None
        else:
            # Escape '
            return answer.replace(r"'", r"\'")
    
    if default is None:
        to_ask = question + ': '
    else:
        to_ask = question + ' [' + default + ']: '
    
    answer = do_ask(to_ask, default)
    while compulsory and answer is None:
        print "An answer to this question is compulsory"
        answer = do_ask(to_ask, default)
    
    while restrict != None and answer not in restrict:
        print "This is not an allowed answer"
        answer = do_ask(to_ask, default)
    
    return answer

def ask_yes_no(to_ask, default):
    return {
        'y': True,
        'n': False,
    }[ask(to_ask + ' (y/n)', default, False, ['y', 'n'])]

def main(settings_fd, database_name=None, database_user=None, database_pass=None):
    config = """# This file is automatically generated by the Molly Project
# Please see http://docs.mollyproject.org/ for reference documentation

from oauth.oauth import OAuthSignatureMethod_PLAINTEXT
import os.path, imp
from molly.conf.settings import Application, extract_installed_apps, Authentication, ExtraBase, Provider
from molly.utils.media import get_compress_groups

molly_root = imp.find_module('molly')[1]
project_root = os.path.normpath(os.path.dirname(__file__))

"""
    
    print """
Welcome to the Molly configuration generator

You will be asked a number of questions relating to how you would like Molly to
be configured. Once complete, you will end up with a file called settings.py
in your current directory

--------------------------------------------------------------------------------

Let's get started with some basic questions.

First, we need to define some administrators for your site. Each administrator
will require a full name and e-mail address.
"""
    
    # Get administrators
    def get_admin(required=False):
        
        if not required:
            print "\nIf you do not want to define any more administrators, you can just"
            print "press the Enter key to continue"
            compulsory = False
        else:
            compulsory = True
        
        admin_name = ask('Administrator Name', compulsory=compulsory)
        if admin_name is None:
            return
        else:
            admin_email = ask('Administrator Email', compulsory=True)
            next = get_admin()
            if next is None:
                return [(admin_name, admin_email)]
            else:
                return [(admin_name, admin_email)] + next
    
    config += 'ADMINS = (\n'
    for admin_name, admin_email in get_admin(True):
        config += "    ('%s', '%s'),\n" % (admin_name, admin_email)
    config += """)

MANAGERS = ADMINS
"""
    
    # Debug mode
    
    print """
--------------------------------------------------------------------------------

Would you like to run Molly in debug mode? This is useful as you get started,
but is not recommended in a production environment."""
    
    config += """
# DEBUG mode is not recommended in production
"""
    config += "\nDEBUG = %s\n" % str(ask_yes_no('Enable debug mode?', 'y'))
    config += "DEBUG_SECURE = DEBUG\n"
    config += "TEMPLATE_DEBUG = DEBUG\n"
    
    config += """

# The following settings are sensible defaults. Change if need be. 
LANGUAGE_CODE = 'en-gb'
TIME_ZONE = 'Europe/London'
USE_I18N = True
SITE_ID = 1

# Site name is used extensively in templates to name the site
SITE_NAME = '%s'

# Molly can automatically generate the urlpatterns, so it's recommended by
# default to use Molly's urls.py. This doesn't work if you have non-Molly apps
# and may require a custom urls.py to be written
ROOT_URLCONF = 'molly.urls'
""" % ask ('What would you like to call your site?',
           compulsory=True)
    
    # Databases - assume PostGIS
    def write_database(name, user, pw):
        return """
# The connection to your database is configured below. We assume you're using
# PostGIS
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'HOST': 'localhost',
        'NAME': '%s',
        'USER': '%s',
        'PASSWORD': '%s',
    }
}
"""  % (name, user, pw)
    
    if database_name != None and database_user != None and database_pass != None:
        config += write_database(database_name, database_user, database_pass)
    else:
        print """
--------------------------------------------------------------------------------

The next step is to configure your database settings. We're assuming you're
using PostGIS (the recommended configuration), if this is not true, then you
must alter settings.py later."""
        config += write_database(
            ask('Database Name', default=database_name, compulsory=True),
            ask('Database Username', default=database_user, compulsory=True),
            ask('Database Password', default=database_pass, compulsory=True)
        )
    
    print "\n--------------------------------------------------------------------------------"
    
    def get_cache(default='/var/cache/molly'):
        cache = ask('Where would you like cache files to be stored?', default=default, compulsory=True)
        if cache[-1] == '/': # strip trailing /
            cache = cache[:-1]
        if not os.path.isdir(cache):
            create = ask_yes_no('That path does not seem to exist, would you like to create it?', 'y')
            if create:
                try:
                    os.makedirs(cache)
                except os.error:
                    print "An error occured creating that directory..."
                    return get_cache(default=cache)
            else:
                print "The cache directory must exist for installation to continue"
                return get_cache(default=cache)
        else:
            try:
                if os.geteuid() == 0:
                    molly_uid, molly_gid = pwd.getpwnam('molly')[2:4]
                    os.chown(cache, molly_uid, molly_gid)
            except Exception:
                pass
            return cache
    
    config += """
# The CACHE_DIR is used by default to store cached map tiles, generated static
# maps, markers, external images, etc
CACHE_DIR = '%s'
""" % get_cache()
    
    # API keys
    print """
--------------------------------------------------------------------------------

Now we'll need to know your API keys for some applications. If you don't have
a key, then you can simply skip the question - however this means that the
corresponding functionality will be disabled until you manually override it."""
    
    cloudmade = ask('What is your Cloudmade API key?')
    google_analytics = ask('What is your Google Analytics API key?')
    
    config += """
# API keys are used to access particular services
API_KEYS = {
    'cloudmade': '%s',
    'google_analytics': '%s',
}
""" % (str(cloudmade), str(google_analytics))
    
    # Applications
    
    print """
--------------------------------------------------------------------------------

Now we're going to ask you some questions relating to the configuration of the
applications in Molly.

Some questions can be skipped by leaving the blank. If this is done, then it
will disable the feature that is being asked about, or some sensible default is
used."""
    
    config += """

# The meat of Molly - application configuration
APPLICATIONS = [
"""
    
    # Home application - always
    config += """
    Application('molly.apps.home', 'home', 'Home',
        display_to_user = False,
    ),
    """
    
    # Desktop application - ask for settings - blog feed, Twitter, blog URL (to ignore)
    # optional
    if ask_yes_no('Would you like to enable the desktop application?', 'y'):
        config += """
    Application('molly.apps.desktop', 'desktop', 'Desktop',
        display_to_user = False,"""
        twitter_username = ask('Please enter your Twitter username')
        if twitter_username != None:
            config += "\n        twitter_username = '%s'," % twitter_username
            twitter_ignore_urls = ask('Please enter a URL prefix to ignore in the Twitter feed')
            if twitter_ignore_urls != None:
                config += "\n        twitter_ignore_urls = 'http://post.ly/'," % twitter_ignore_urls
        blog_rss_url = ask('Please enter your blog RSS URL')
        if blog_rss_url != None:
            config += "\n        blog_rss_url = 'http://feeds.feedburner.com/mobileoxford',"
        config += """
    ),
    """
    
    # Contact Search (with MIT's LDAP provider) - optional
    if ask_yes_no('Would you like to enable the contact search application?', 'y'):
        ldap_url = ask('What is the URL of the LDAP server to use for contact searching?')
        if ldap_url != None:
            config += """
    Application('molly.apps.contact', 'contact', 'Contact search',
        provider = Provider('molly.apps.contact.providers.LDAPContactProvider',
                             url='%s', base_dn='%s'),
    ),
    """ % (ldap_url, ask('What is the base DN to use for searching the LDAP tree?'))
        else:
            print "Skipping LDAP configuration, no URL specified...\n"
    
    # Library search - optional
    # Need: Z39.50 host, database, syntax, port (210)
    if ask_yes_no('Would you like to enable the library search application?', 'y'):
        config += """
    Application('molly.apps.library', 'library', 'Library search',
        provider = Provider('molly.apps.library.providers.Z3950',
                            host = '%s',
                            port = %s,
                            database = '%s',
                            syntax = '%s'),
    ),
    """ % (ask('Please enter the hostname of your Z39.50 catalogue', compulsory = True),
           ask('Please enter the port number of the Z39.50 catalogue', default='210', compulsory = True),
           ask('Please enter the name of the database to search on', compulsory=True),
           ask('Please enter the syntax your server uses for results', default='USMARC', compulsory=True)
          )
    
    # Podcasts - optional
    # URL to OPML (optional)
    # URLs of RSS feed (optional)
    # URLs of podcast producer feeds (optional)
    def get_opml_data():
        print "\nLeave blank to skip adding an OPML feed"
        url = ask('Enter the URL of a podcast OPML feed to add')
        if url is None:
            return None
        else:
            rss_re = ask('Enter a regular expression to extract the feed slug from the RSS URL\n')
            if rss_re is None:
                return None
            else:
                return (url, rss_re)
    
    def get_rss_data():
        print "\nLeave blank to skip adding an RSS feed"
        slug = ask('Enter the slug for a podcast RSS feed')
        if slug is None:
            return None
        else:
            url = ask('Enter the URL for this RSS feed')
            if url is None:
                return None
            else:
                return (slug, url)
    
    if ask_yes_no('Would you like to enable the podcasts application?', 'y'):
        config += """
    Application('molly.apps.podcasts', 'podcasts', 'Podcasts',
        providers = ["""
        opml = get_opml_data()
        while opml != None:
            url, rss_re = opml
            config += """
            Provider('molly.apps.podcasts.providers.OPMLPodcastsProvider',
                url = '%s',
                rss_re = r'%s'
            ),
    """ % (url, rss_re)
            opml = get_opml_data()
        rss = get_rss_data()
        if rss != None:
            config += """
            Provider('molly.apps.podcasts.providers.RSSPodcastsProvider',
                podcasts = ["""
            while rss != None:
                slug, url = rss
                config += "                    ('%s', '%s'),\n" % (slug, url)
                rss = get_rss_data()
            config += """                ],
            ),"""
        print "\nLeave blank to skip adding Podcast Producer feeds"
        pp = ask('Please enter the URL for this Podcast Producer feed')
        while pp != None:
            config += """
            Provider('molly.apps.podcasts.providers.PodcastProducerPodcastsProvider',
                url = '%s',
            ),
    """ % pp
            pp = ask('Please enter the URL for this Podcast Producer feed')
        config += """        ]
        ),
    """
    
    # Webcams - optional
    if ask_yes_no('Would you like to enable the webcam application?', 'y'):
        config += """
    Application('molly.apps.webcams', 'webcams', 'Webcams'),
    """
    
    # Weather - optional, BBC location ID
    if ask_yes_no('Would you like to enable the weather application?', 'y'):
        id = ask('What is the BBC Weather ID to use?', compulsory=True)
        config += """
    Application('molly.apps.weather', 'weather', 'Weather',
        location_id = 'bbc/%s',
        provider = Provider('molly.apps.weather.providers.BBCWeatherProvider',
            location_id = %s,
        ),
    ),
    """ % (id, id)
    
    # Service status - optional, RSS feeds
    def get_service_status_rss():
        url = ask('Enter the URL of an RSS feed to add')
        if url is None:
            return None
        else:
            name = ask('Enter the name of this RSS feed')
            if name is None:
                return None
            else:
                slug = ask('Enter the slug for this RSS feed')
                return (url, name, slug)
    
    if ask_yes_no('Would you like to enable the service status application?', 'y'):
        config += """
    Application('molly.apps.service_status', 'service_status', 'Service status',
        providers = ["""
        print "\nLeave blank to skip adding a service status feed"
        feed = get_service_status_rss()
        while feed != None:
            url, name, slug = feed
            config += """
            Provider('molly.apps.service_status.providers.RSSModuleServiceStatusProvider',
                name='University of Example IT Services',
                slug='it',
                url='http://www.example.ac.uk/it/status.rss')
    """ % (url, name, slug)
            feed = get_service_status_rss()
        config += """        ],
        ),
    """
    
    # Search - always - GSA Provider = optional
    
    config += """
    Application('molly.apps.search', 'search', 'Search',
        providers = [
            Provider('molly.apps.search.providers.ApplicationSearchProvider'), """
    if ask_yes_no('Would you like to enable searching using a Google Search Applicance', 'n'):
        config += """
            Provider('molly.apps.search.providers.GSASearchProvider',
                search_url = '%s',
                domain = '%s',
                # Set a regular expression below here to clear up the title of
                # returned pages
                #title_clean_re = r'molly \| (.*)',
            ),""" % (ask('What is the URL of your Google Search Appliance?', compulsory=True),
                     ask('What is the URL of the site to restrict searches to?', compulsory=True))
    config += """
        ],
        # Uncomment if you're using a query expansion file
        #query_expansion_file = os.path.join(project_root, 'data', 'query_expansion.txt'),
        display_to_user = False,
    ),
    """
    
    # Feeds always
    config += """
    Application('molly.apps.feeds', 'feeds', 'Feeds',
        providers = [
            Provider('molly.apps.feeds.providers.RSSFeedsProvider'),
        ],
        display_to_user = False,
    ),
    """
    
    # News - optional
    if ask_yes_no('Would you like to enable the news application?', 'y'):
        config += """
    Application('molly.apps.feeds.news', 'news', 'News'),
    """
    
    # Events - optional
    if ask_yes_no('Would you like to enable the events application?', 'n'):
        config += """
    Application('molly.apps.feeds.events', 'events', 'Events'),
    """
    
    # Maps - always
    config += """
    Application('molly.maps', 'maps', 'Maps',
        display_to_user = False,
    ),
    """
    
    # Geolocation - always
    # ask if there's a longitude, latitude, distance preference
    # Cloudmade (only if API key set earlier) - limit to locality?
    
    config += """
    Application('molly.geolocation', 'geolocation', 'Geolocation',
    """
    
    print "http://itouchmap.com/latlong.html can help you find the latitude and longitude"
    print "of a point"
    lon = ask('What is the longitude of your location?', compulsory=True)
    lat = ask('What is the latitude of your location?', compulsory=True)
    
    print
    print "By default, Molly searches the entire planet for addresses entered when"
    print "manually specifying your current location, but often this is undesirable",
    if ask_yes_no('Would you like to limit geocoding searches?', 'y'):
        config += """
        prefer_results_near = (%s, %s, %s),""" % (lon, lat,
                                                  ask('How far around your location (in metres) should geocoding results be considered for?', compulsory=True, default='10000'))
    config += """
        providers = [
            Provider('molly.geolocation.providers.PlacesGeolocationProvider'),"""
    if cloudmade != None:
        config += """
            Provider('molly.geolocation.providers.CloudmadeGeolocationProvider', """
        locality = ask('Which placename would you like Cloudmade geocoding requests to be restricted to?\n')
        if locality != None:
            config += "\n                search_locality = 'Oxford',"
        config += """
            ),"""
    config += """
        ],
        display_to_user = False,
    ),
    """
    
    # Feedback - always
    config += """
    Application('molly.apps.feedback', 'feedback', 'Feedback',
        display_to_user = False,
    ),
    """
    
    # Feature suggestions - always
    config += """
    Application('molly.apps.feature_vote', 'feature_vote', 'Feature suggestions',
        display_to_user = False,
    ),
    """
    
    # External media - always
    config += """
    Application('molly.external_media', 'external_media', 'External Media',
        display_to_user = False,
    ),
    """
    
    # WURFL - always (expose view)
    config += """
    Application('molly.wurfl', 'device_detection', 'Device detection',
        display_to_user = False,
        expose_view = True,
    ),
    """
    
    # Stats (ask)
    enable_stats = ask_yes_no('Would you like to enable hit logging?', 'y')
    if enable_stats:
        config += """
    Application('molly.apps.stats', 'stats', 'Statistics',
         display_to_user = False,
     ), 
    """
    
    # URL shortener - always
    config += """
    Application('molly.url_shortener', 'url_shortener', 'URL Shortener',
        display_to_user = False,
    ),
    """
    
    # Molly utilities - always
    config += """
    Application('molly.utils', 'utils', 'Molly utility services',
        display_to_user = False,
    ),
    """
    
    # Auth - always
    config += """
    Application('molly.auth', 'auth', 'Authentication',
        display_to_user = False,
        secure = True,
        unify_identifiers = ('weblearn:id',),
    ),
    """
    
    # Sakai - ask (including simplied OAuth config) - ask for host, service_name,
    # which tools to be enabled (signup, poll)
    if ask_yes_no('Would you like to enable Sakai integration?', 'n'):
        url = ask('What is the URL to your Sakai instance?', compulsory=True)
        service_name = ask('What is the name of your Sakai deployment?', default='WebLearn', compulsory='True')
        config += """
    Application('molly.apps.sakai', 'sakai', '%s',
        host = '%s',
        service_name = '%s',
        secure = True,
        tools = [
    """ % (service_name, url, service_name)
        if ask_yes_no('Would you like to enable signups in Sakai?', 'y'):
            config += "            ('signup', 'Sign-ups'),\n"
        if ask_yes_no('Would you like to enable polls in Sakai?', 'y'):
            config += "            ('poll', 'Polls'),\n"
        config += """        ],
        extra_bases = (
            ExtraBase('molly.auth.oauth.views.OAuthView',
                secret = %s,
                signature_method = OAuthSignatureMethod_PLAINTEXT(),
                base_url = '%s/oauth-tool/',
                request_token_url = 'request_token',
                access_token_url = 'access_token',
                authorize_url = 'authorize',
            ),
        ),
        enforce_timeouts = False,
        identifiers = (
            ('weblearn:id', ('id',)),
            ('weblearn:email', ('email',)),
        ),
    ),
    """ % (ask('What is your Sakai OAuth secret?', compulsory=True), url)
    
    # Places - always, start with some default nearby-entity-types, configure more
    # later, no associations, configure more later
    # ACIS Live? y/n
    # BBC TPEG y/n - UK wide or limit to county?
    # LDB - do you have a token?
    # Naptan - which areas? (default to HTTP)
    # OSM - longitude/latitude (compute +/- automatically)
    # Postcodes (postal region)
    
    config += """
    Application('molly.apps.places', 'places', 'Places',
        providers = ["""
    
    print
    print "The NaPTAN is a database of public transport 'access nodes' in the UK"
    print "We use this to find bus stops and train stations near you. The NaPTAN is"
    print "split up into areas by ATCO code. You can find a list of area codes at"
    print "http://www.dft.gov.uk/naptan/smsPrefixes.htm (please note it is the column"
    print "header ATCO that is used here). All area codes must be three digits long"
    print "and padded with 0s. e.g., Bedfordshire is listed in the table as 20, but"
    print "in the database is stored as 020 - please prefix with 0s to make it up to"
    print "3 digits long"
    print
    print "To import multiple areas, please answer the questions multiple times, and"
    print "leave blank to finish. Entering no areas will mean you will not have any"
    print "bus stops or train stations in your database."
    
    area = ask('What is the ATCO area code you would like to import?')
    if area != None:
        areas = []
        while area != None:
            areas += area
            area = ask('What is the ATCO area code you would like to import?')
        config += """
            Provider('molly.apps.places.providers.NaptanMapsProvider',
                method='http',
                areas=('%s',),
            ),""" % "','".join(areas)
    
    print
    print "Please note that a postcode prefix is the letters at the start of a postcode"
    print "e.g., YO for YO10 5DD or OX for OX2 6NN. You can enter multiple prefixes here"
    print "(one at a time), or leave blank to not use postcodes"
    
    postcode = ask('What postcode area prefix would you like to import?')
    if postcode != None:
        postcodes = []
        while postcode != None:
            postcodes += postcode
            postcode = ask('What postcode area prefix would you like to import?')
        config += """
            Provider('molly.apps.places.providers.PostcodesMapsProvider',
                codepoint_path = CACHE_DIR + '/codepo_gb.zip',
                import_areas = ('%s',),
            ),""" % "','".join(postcodes)
    if ask_yes_no('Would you like to display real time bus information? (where supported)', 'y'):
        config += """
            'molly.apps.places.providers.ACISLiveMapsProvider',"""
    
    if ask_yes_no('Would you like to display points of interest from OpenStreetMap?', 'y'):
        config += """
            Provider('molly.apps.places.providers.OSMMapsProvider',
                     lat_north=%f, lat_south=%f,
                     lon_west=%f, lon_east=%f
            ),""" % (float(lat) + 0.2, float(lat) - 0.2,
                     float(lon) - 0.2, float(lon) + 0.2)
    
    print "You can obtain tokens for the LDB API from National Rail Enquiries"
    ldb_token = ask('In order to use the National Rail Live Departure Board API, please\nenter your token')
    if ldb_token != None:
        config += """
            Provider('molly.apps.places.providers.LiveDepartureBoardPlacesProvider',
                token = '%s'
            ),""" % ldb_token
    
    print "We can import travel alert data from the BBC to show on the transport page."
    print "Unfortunately the BBC don't publish a single list of all of their feeds, so"
    print "you have to guess the URL. If you get the URL for your local transport page"
    print "from http://www.bbc.co.uk/travelnews/, then the last part of the URL is what"
    print "is needed below. Please use 'rtm' for national roads."
    print
    print "e.g., for 'Braford & West Yorkshire', the URL is"
    print "http://www.bbc.co.uk/travelnews/bradford/, so 'bradford' should be entered"
    print "below. Leave blank to skip."
    tpeg_zone = ask('Which travel news area would you like to import?')
    use_tpeg = False
    while tpeg_zone != None:
        use_tpeg = True
        config += """
            Provider('molly.apps.places.providers.BBCTPEGPlacesProvider',
                url='http://www.bbc.co.uk/travelnews/tpeg/en/local/rtm/%s_tpeg.xml',
            ),""" % tpeg_zone
        tpeg_zone = ask('Which travel news area would you like to import?')
    config += """
        ],
        nearby_entity_types = (
            ('Transport', (
                'bicycle-parking', 'bus-stop', 'car-park', 'park-and-ride',
                'taxi-rank', 'train-station')),
            ('Amenities', (
                'atm', 'bank', 'bench', 'medical', 'post-box', 'post-office',
                'public-library', 'recycling', 'bar', 'food', 'pub')),
            ('Leisure', (
                'cinema', 'theatre', 'museum', 'park', 'swimming-pool',
                'sports-centre', 'punt-hire')),
        ),

    ),
    """
    
    # Transport y/n
    #  train station CRS code?
    if ask_yes_no('Would you like to enable the transport application?', 'y'):
        config += """
    Application('molly.apps.transport', 'transport', 'Transport',
    """
        print "You can find CRS codes at http://www.nationalrail.co.uk/stations/codes/"
        config += "        train_station = 'crs:%s'," % ask('What is the CRS code of the rail station to show?', compulsory=True)
        config += """
        nearby = {
            'park_and_rides': ('park-and-ride', 5, True, False),
            'bus_stops': ('bus-stop', 5, False, True),
        },
    """
        if use_tpeg:
            config += "        travel_alerts = True,"
        config += """
        ),
    """
    
    config += """
]
"""
    
    # Middleware - will need to know if stats app is enabled, as this changes if the
    # middleware is included or not, also, need to ask if we want Molly to handle
    # errors (E-mail errors)
    
    config += """

# Middleware classes alter requests and responses before/after they get
# handled by the view. They're useful in providing high-level global
# functionality
MIDDLEWARE_CLASSES = (
    'molly.wurfl.middleware.WurflMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'molly.utils.middleware.ErrorHandlingMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'molly.auth.middleware.SecureSessionMiddleware',
"""
    if enable_stats:
        config += "    'molly.apps.stats.middleware.StatisticsMiddleware',"
    else:
        config += "    #'molly.apps.stats.middleware.StatisticsMiddleware',"
    config += """
    'molly.url_shortener.middleware.URLShortenerMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
)
"""
    
    # Template context processors - will need to know if Google Analytics is used
    # earlier
    
    config += """
# Each entity has a primary identifier which is used to generate the absolute
# URL of the entity page. We can define a list of identifier preferences, so
# that when an entity is imported, these identifier namespaces are looked at in
# order until a value in that namespace is chosen. This is then used as the
# primary identifer.
#IDENTIFIER_SCHEME_PREFERENCE = ('atco', 'osm', 'naptan', 'postcode', 'bbc-tpeg')

# This setting defines which context processors are used - this can affect what
# is available in the context of a view
TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.request',
    'django.core.context_processors.i18n',
    'molly.utils.context_processors.ssl_media',
    'django.contrib.messages.context_processors.messages',
    'molly.wurfl.context_processors.wurfl_device',
    'molly.wurfl.context_processors.device_specific_media',
    'molly.geolocation.context_processors.geolocation',
    'molly.utils.context_processors.full_path',
    'molly.utils.context_processors.site_name',"""
    if google_analytics != None:
        config += """\n    'molly.utils.context_processors.google_analytics',"""
    else:
        config += """\n    #'molly.utils.context_processors.google_analytics',"""
    config += """
    'django.core.context_processors.csrf',
)
"""
    
    # Static files, etc
    config += """
# This setting defines where Django looks for templates when searching - it
# assumes your overriding templates are defined in '/your/project/templates'
# and you want to have the Molly defaults as a fallback
TEMPLATE_DIRS = (
    os.path.join(project_root, 'templates'),
    os.path.join(molly_root, 'templates'),
)

# This setting changes how Django searches for templates when rendering. The
# default is fine
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
    'django.template.loaders.eggs.load_template_source',
    'molly.utils.template_loaders.MollyDefaultLoader'
)

# Non-Molly apps get added here (plus, tell Django about Molly apps)
INSTALLED_APPS = extract_installed_apps(APPLICATIONS) + (
    'django.contrib.auth',
    'django.contrib.admin',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.gis',
    'django.contrib.comments',
    'molly.batch_processing',
    'staticfiles',
    'compress',
    'south',
)

# Defines where markers get generated
MARKER_DIR = os.path.join(CACHE_DIR, 'markers')

# This shouldn't need changing
SRID = 27700

# Settings relating to staticfiles
STATIC_ROOT = os.path.join(project_root, 'media') # the location on disk where media is stored
STATIC_URL = '/media/' # The URL used to refer to media
STATICFILES_DIRS = (
    ('', os.path.join(project_root, 'site_media')), # Custom overriding
    ('', os.path.join(molly_root, 'media')), # Molly default media
    ('markers', MARKER_DIR), # Markers
)
ADMIN_MEDIA_PREFIX = STATIC_URL + 'admin/'

# Settings relating to django-compress
COMPRESS_SOURCE = STATIC_ROOT
COMPRESS_ROOT = STATIC_ROOT
COMPRESS_URL = STATIC_URL
COMPRESS_CSS, COMPRESS_JS = get_compress_groups(STATIC_ROOT)
COMPRESS_CSS_FILTERS = ('molly.utils.compress.MollyCSSFilter',) # CSS filter is custom-written since the provided one mangles it too much
COMPRESS_CSSTIDY_SETTINGS = {
    'remove_bslash': True, # default True
    'compress_colors': True, # default True
    'compress_font-weight': True, # default True
    'lowercase_s': False, # default False
    'optimise_shorthands': 0, # default 2, tries to merge bg rules together and makes a hash of things
    'remove_last_': False, # default False
    'case_properties': 1, # default 1
    'sort_properties': False, # default False
    'sort_selectors': False, # default False
    'merge_selectors': 0, # default 2, messes things up
    'discard_invalid_properties': False, # default False
    'css_level': 'CSS2.1', # default 'CSS2.1'
    'preserve_css': False, # default False
    'timestamp': False, # default False
    'template': 'high_compression', # default 'highest_compression'
}
COMPRESS_JS_FILTERS = ('compress.filters.jsmin.JSMinFilter',)
COMPRESS = not DEBUG     # Only enable on production (to help debugging)
COMPRESS_VERSION = True  # Add a version number to compressed files.
"""
    
    # Write out config
    settings_fd.write(config)
    settings_fd.close()
    
    print """
Please note that this configuration script does not cover all possible
settings or configurations of Molly, and more advanced setup may require
editing the resulting file directly. Please read the documentation for a
full reference of the available settings

Thanks for configuring Molly!
"""

if __name__ == '__main__':
    from optparse import OptionParser
    
    if os.path.exists('settings.py'):
        print "Cannot continue - a settings.py file already exists"
        sys.exit()
    else:
        settings_fd = open('settings.py', 'w')

    parser = OptionParser()
    parser.add_option("-n", "--database-name")
    parser.add_option("-u", "--database-user")
    parser.add_option("-p", "--database-pass")
    
    (options, args) = parser.parse_args()
    main(settings, gf, options.database_name, options.database_user, options.database_pass)