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
        params_dict = self.get_api_params(slide)
        params = urllib.urlencode(params_dict)
        return "%s?%s" % (api_url, params)

    def get_api_params(self, slide):
        """
        Returns the parameters required for a SlideShare api call.
        """
        ts = int(time.time())
        params_dict = {
                       'api_key' : slide.api_keys['slideshare_api_key'],
                       'ts' : ts,
                       'hash' : sha.new(slide.api_keys['slideshare_api_secret'] + str(ts)).hexdigest(),
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
                'embed_code': SlideShareSuite.strip_embed_extras(response_json['Embed']),
                'publish_datetime': parser.parse(response_json['Created']),
                'thumbnail_url': response_json['ThumbnailURL'],
                'user': response_json['Username'],
                'user_url': "http://www.slideshare.net/%s" % response_json['Username'],
                'view_count': int(response_json['NumViews']),
                'slide_count': int(response_json['NumSlides']),
                'language': response_json['Language'],
                }

        if 'Tags' in response_json and 'Tag' in response_json['Tags']:
            tags = response_json['Tags']['Tag']
            if isinstance(tags, list):
                data['tags'] = [tag['#text'] for tag in tags]
            elif '#text' in tags:
                data['tags'] = [tags['#text'],]
        
#        # Removing for now b/c links have expiration date (very short)
#        if int(response_json['Download']):
#            data['file_url'] = response_json['DownloadUrl']
#            data['file_format'] = response_json['Format']

        return data


class SlideShareSuite(BaseSuite):
    """
    Suite for slideshare.net. Currently only supports oembed.
    """
    provider_name = 'SlideShare'
    slide_regex = r'https?://([^/]+\.)?slideshare.net/(?P<username>\w+)/(?P<presentation_slug>\w+)'

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

registry.register(SlideShareSuite)
