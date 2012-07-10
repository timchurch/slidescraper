from slidescraper.suites import BaseSuite, registry, SuiteMethod, OEmbedMethod
import json
import time
import sha
import urllib, urllib2
from dateutil import parser
import xmltodict
from bs4 import BeautifulSoup, SoupStrainer
from pprint import pprint


class SlideShareOEmbedMethod(OEmbedMethod):
    """
    SlideShare adds extra, non-standard total_slides field to OEmbed

    :param endpoint: The endpoint url for this suite's oembed API.
    """
    fields = set(['title', 'user', 'user_url', 'thumbnail_url', 'embed_code', 'slide_count'])

    def process(self, response):
        parsed = json.loads(response.text)
        data = {
            'title': parsed['title'],
            'user': parsed['author_name'],
            'user_url': parsed['author_url'],
            'thumbnail_url': parsed['thumbnail'],
            'embed_code': SlideShareSuite.strip_embed_extras(parsed['html']),
            'slide_count': parsed['total_slides']
        }
        return data


class SlideShareApiMethod(SuiteMethod):
    fields = set(('link', 'title', 'description', 'guid', 'thumbnail_url',
                  'publish_datetime', 'tags', 'user', 'user_url',
                  'embed_code', 'view_count', 'slide_count', 'language'))

    def get_url(self, slide):
        if slide.api_keys is None or 'slideshare_api_key' not in slide.api_keys:
            raise ValueError("API key must be set for SlideShare API requests.")
        if 'slideshare_api_secret' not in slide.api_keys:
            raise ValueError("API secret must be set for SlideShare API requests.")
        
        api_url = u"http://www.slideshare.net/api/2/get_slideshow"
        params_dict = self.get_api_params(api_key=slide.api_keys['slideshare_api_key'],
                                          api_secret=slide.api_keys['slideshare_api_secret'],
                                          url=slide.url)
        params = urllib.urlencode(params_dict)
        return "%s?%s" % (api_url, params)

    @classmethod
    def get_api_params(cls, api_key=None, api_secret=None, url=None, user=None, tag=None, group=None):
        """
        Returns the parameters required for a SlideShare api call.
        """
        ts = int(time.time())
        params_dict = {
                       'api_key' : api_key,
                       'ts' : ts,
                       'hash' : sha.new(api_secret + str(ts)).hexdigest(),
                       'detailed': 1,
                       }

        # Set method specific parameters
        if url:
            params_dict['slideshow_url'] = url
        elif user:
            params_dict['username_for'] = user
        elif tag:
            params_dict['tag'] = tag
        elif group:
            params_dict['group_name'] = group

        return params_dict

    def process(self, response):
        xml = response.text
        response_json = xmltodict.parse(xml)
        return SlideShareApiMethod.parse_api_data(response_json['Slideshow'])

    @classmethod
    def parse_api_data(cls, api_json):
        """
        Converts API JSON response to a dictionary for loading a Slides object
        """
        data = {'guid': 'slideshare:%s' % api_json['ID'],
                'title': api_json['Title'],
                'link': api_json['URL'],
                'description': api_json['Description'],
                'embed_code': SlideShareSuite.build_iframe_embed_code(api_json['ID']),
                'publish_datetime': parser.parse(api_json['Created']),
                'thumbnail_url': api_json['ThumbnailURL'],
                'user': api_json['Username'],
                'user_url': "http://www.slideshare.net/%s" % api_json['Username'],
                'view_count': int(api_json['NumViews']),
                'slide_count': int(api_json['NumSlides']),
                'language': api_json['Language'],
                }

        # Embed code
        soup = BeautifulSoup(api_json['Embed'])
        embed_width = None
        embed_height = None
        for tag in soup.find_all("object", limit=1):
            embed_width = tag['width']
            embed_height = tag['height']
        data['embed_code'] = SlideShareSuite.build_iframe_embed_code(api_json['ID'], embed_width, embed_height)

        # Overwrite username with full user name
        tags = soup.find_all('a')
        if tags:
            tag = tags.pop()
            data['user'] = tag.string

        if 'Tags' in api_json and api_json['Tags'] and 'Tag' in api_json['Tags']:
            tags = api_json['Tags']['Tag']
            if isinstance(tags, list):
                data['tags'] = [tag['#text'] for tag in tags]
            elif '#text' in tags:
                data['tags'] = [tags['#text'],]
        
#        # Removing for now b/c links have expiration date (very short)
#        if int(api_json['Download']):
#            data['file_url'] = api_json['DownloadUrl']
#            data['file_format'] = api_json['Format']

#        pprint(data)
        return data


class SlideShareSuite(BaseSuite):
    """
    Suite for slideshare.net. Currently only supports oembed.
    """
    provider_name = 'SlideShare'
    slide_regex = r'https?://([^/]+\.)?slideshare.net/(?P<username>\w+)/(?P<presentation_slug>\w+)'
    # Example URLs:
    #     http://www.slideshare.net/zeeg/djangocon-2010-scaling-disqus

    feed_regex = r'https?://([^/]+\.)?slideshare.net/rss/user/(?P<username>\w+)(/presentations)?'
    # Example URLs:
    #     http://www.slideshare.net/rss/user/ihower
    #     http://www.slideshare.net/rss/user/ihower/presentations

    methods = (SlideShareOEmbedMethod(u"http://www.slideshare.net/api/oembed/2"),
               SlideShareApiMethod(),)

    @classmethod
    def strip_embed_extras(cls, embed_code):
        """
        SlideShare add header text, footer text, and a fixed width container div by default.
        This will remove those and just leave the iframe/object.
        """
        start_tag = '<iframe'
        end_tag = '</iframe>'

        start = embed_code.find(start_tag)
        end = embed_code.rfind(end_tag)

        if start < 0:
            start_tag = '<object'
            start = embed_code.find(start_tag)
        if end < 0:
            end_tag = '</object>'
            end = embed_code.rfind(end_tag)

        end_tag_len = len(end_tag)
        new_embed_code = embed_code[start:end+end_tag_len]
        return new_embed_code

    @classmethod
    def build_iframe_embed_code(cls, slidshare_id, width=425, height=355):
        return "<iframe src=\"http://www.slideshare.net/slideshow/embed_code/{0}\" width=\"{1}\" height=\"{2}\" frameborder=\"0\" marginwidth=\"0\" marginheight=\"0\" scrolling=\"no\" allowfullscreen></iframe>".format(slidshare_id, width, height) 

    def get_feed_url(self, feed_url, feed=None):
        """
        Rewrites a feed url into an api request url so that crawl can work, 
        and because more information can be retrieved from the api.

        ONLY SUPPORTS USER FEEDS FOR NOW
        """
        match = self.feed_regex.match(feed_url)
        if match and match.group('username'):
            username = match.group('username')
            SLIDESHARE_API_BASE_URL = "http://www.slideshare.net/api/2/"
            API_METHOD = "get_slideshows_by_user"
            params_dict = SlideShareApiMethod.get_api_params(api_key=feed.api_keys['slideshare_api_key'],
                                                             api_secret=feed.api_keys['slideshare_api_secret'],
                                                             user=username)
            params = urllib.urlencode(params_dict)
            return "%s%s?%s" % (SLIDESHARE_API_BASE_URL, API_METHOD, params)
        return feed_url

    def get_feed_response(self, feed, feed_url):
        """
        Override default to parse API result XML, not as a real feed
        """
        response = urllib2.urlopen(feed_url, timeout=5)
        response_text = response.read()
        parsed_response = xmltodict.parse(response_text)
        return parsed_response

    def get_feed_title(self, feed, response):
        if 'User' in response:
            return u'Slideshows by User %s on SlideShare' % response['User']['Name']
        elif 'Tag' in response:
            return u"Slideshows by Tag %s on SlideShare" % response['Tag']['Name']
        return ''

    def get_feed_description(self, feed, response):
        return ''

    def get_feed_thumbnail_url(self, feed, response):
        return ''

    def get_feed_guid(self, feed, response):
        return None

    def get_feed_last_modified(self, feed, response):
        """ Approximate last modified by checking last update of latest slideshow"""
        type_ = None
        if 'User' in response:
            type_ = 'User'
        elif 'Tag' in response:
            type_ = 'Tag'

        if type_ and 'Slideshow' in response[type_]:
            slideshows = response[type_]['Slideshow']
            last_update = max([parser.parse(slideshow['Updated']) for slideshow in slideshows])

#            # Only check updated date of most recent slideshow
#            #     Not as accurate but faster and a good estimate
#            most_recent_slideshow = slideshows[0]
#            if 'Updated' in most_recent_slideshow:
#                last_update = parser.parse(most_recent_slideshow['Updated'])
#                return last_update

            return last_update

        return None

    def get_feed_etag(self, feed, response):
        return None

    def get_feed_webpage(self, feed, response):
        if 'User' in response:
            return u'http://www.slideshare.net/%s' % response['User']['Name']
        elif 'Tag' in response:
            return u'http://www.slideshare.net/tag/%s' % response['Tag']['Name']
        return ''

    def get_feed_entry_count(self, feed, feed_response):
        return feed_response['User']['Count']

    def get_feed_entries(self, feed, feed_response):
        if feed_response is None: # no more data
            return []
        elif 'User' in feed_response and 'Slideshow' in feed_response['User']:
            return reversed(feed_response['User']['Slideshow'])
        elif 'Tag' in feed_response and 'Slideshow' in feed_response['Tag']:
            return reversed(feed_response['Tag']['Slideshow'])
        return feed_response

    def parse_feed_entry(self, entry):
        return SlideShareApiMethod.parse_api_data(entry)

registry.register(SlideShareSuite)
