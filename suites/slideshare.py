from slidescraper.suites import BaseSuite, registry, SuiteMethod, OEmbedMethod
import json
import time
import sha
import urllib
from dateutil import parser
import xmltodict


class SlideShareOEmbedMethod(OEmbedMethod):
    """
    SlideShare adds extra, non-standard total_slides field to OEmbed

    :param endpoint: The endpoint url for this suite's oembed API.
    """
    fields = set(['title', 'user', 'user_url', 'thumbnail_url', 'embed_code', 'slides_count'])

    def process(self, response):
        parsed = json.loads(response.text)
        data = {
            'title': parsed['title'],
            'user': parsed['author_name'],
            'user_url': parsed['author_url'],
            'thumbnail_url': parsed['thumbnail'],
            'embed_code': parsed['html'],
            'slides_count': parsed['total_slides']
        }
        return data


class SlideShareApiMethod(SuiteMethod):
    fields = set(('link', 'title', 'description', 'guid', 'thumbnail_url',
                  'publish_datetime', 'tags', 'user', 'user_url',
                  'view_count', 'slide_count', 'language'))

    def get_url(self, slide):
        if slide.api_keys is None or 'slideshare_key' not in slide.api_keys:
            raise ValueError("API key must be set for SlideShare API requests.")
        if 'slideshare_secret' not in slide.api_keys:
            raise ValueError("API Secret must be set for SlideShare API requests.")
        
        api_url = u"http://www.slideshare.net/api/2/get_slideshow"
        params_dict = self.get_api_params(slide)
        params = urllib.urlencode(params_dict)
#        print "%s?%s" % (api_url, params) # TESTING
        return "%s?%s" % (api_url, params)

    def get_api_params(self, slide):
        """
        Returns the parameters required for a SlideShare api call.
        """
        ts = int(time.time())
        params_dict = {
                       'api_key' : slide.api_keys['slideshare_key'],
                       'ts' : ts,
                       'hash' : sha.new(slide.api_keys['slideshare_secret'] + str(ts)).hexdigest(),
                       'detailed': 1,
                       'slideshow_url' : slide.url,
                       }
        return params_dict

    def process(self, response):
        xml = response.text
        response_json = xmltodict.parse(xml)
        response_json = response_json['Slideshow']

#        from pprint import pprint
#        pprint(response_json)
        
        data = {'guid': 'slideshare:%s' % response_json['ID'],
                'title': response_json['Title'],
                'link': response_json['URL'],
                'description': response_json['Description'],
                'embed_code': response_json['Embed'],
                'publish_datetime': parser.parse(response_json['Created']),
                'thumbnail_url': response_json['ThumbnailURL'],
                'tags': [tag['#text'] for tag in response_json['Tags']['Tag']],
                'user': response_json['Username'],
                'user_url': "http://www.slideshare.net/%s" % response_json['Username'],
                'view_count': int(response_json['NumViews']),
                'slide_count': int(response_json['NumSlides']),
                'language': response_json['Language'],
                }
        
        if response_json['Download']:
            data['file_url'] = response_json['DownloadUrl']
            data['file_url_mimetype'] = response_json['Format']

        return data


class SlideShareSuite(BaseSuite):
    """
    Suite for slideshare.net. Currently only supports oembed.
    """
    provider_name = 'SlideShare'
    slide_regex = r'https?://([^/]+\.)?slideshare.net/(?P<username>\w+)/(?P<presentation_slug>\w+)'

    methods = (SlideShareOEmbedMethod(u"http://www.slideshare.net/api/oembed/2"),
               SlideShareApiMethod(),)

registry.register(SlideShareSuite)
