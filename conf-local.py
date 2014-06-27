AUTHOR = u'Alice Heaton'
SITENAME = u'Alice/Development Notes'
SITEURL = 'http://aliceh75.github.io'

TIMEZONE = 'Europe/London'

DEFAULT_LANG = u'en'

THEME = 'theme'

USE_FOLDER_AS_CATEGORY = True
DEFAULT_DATE = 'fs'

FEED_ALL_ATOM = None
CATEGORY_FEED_ATOM = None
TRANSLATION_FEED_ATOM = None

SUMMARY_MAX_LENGTH = 124
DEFAULT_PAGINATION = False

RELATIVE_URLS = True


def clean_link(link):
    # This is for the live version - local version, do nothing.
    return link


JINJA_FILTERS = {
    'clean_link': clean_link
}





