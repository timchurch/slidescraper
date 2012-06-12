from slidescraper.suites import BaseSuite, registry, SuiteMethod, OEmbedMethod
import json
from bs4 import BeautifulSoup, SoupStrainer
from urlparse import urljoin
from slidescraper.utils.feedparser import struct_time_to_datetime
from pprint import pprint


class SpeakerDeckOEmbedMethod(OEmbedMethod):
    """
    Speaker Deck does not include 'thumbnail_url' in OEmbed
    """
    fields = set(['title', 'user', 'user_url', 'embed_code'])

    def process(self, response):
        parsed = json.loads(response.text)
        data = {
            'title': parsed['title'],
            'user': parsed['author_name'],
            'user_url': parsed['author_url'],
            'embed_code': parsed['html'],
        }
        return data


class SpeakerDeckScrapeMethod(SuiteMethod):
    fields = set(['link', 'title', 'description', 'guid',
                  'thumbnail_url', 'embed_code',
                  'user', 'user_url',
                  'file_url', 'file_format',
#                  'slide_count'  # can't access without js
                  ])

    def get_url(self, slideshow):
        return slideshow.url

    def _strain_filter(self, name, attrs):
        TAG_NAMES = set(['title', ])
        IDS = set(['share_pdf', 'slides_container'])
        CLASSES = set(['description', 'presenter'])
        PROPERTIES = set(['og:image',])

        return name in TAG_NAMES or\
               any((key == 'id' and value in IDS or
                    key == 'class' and value in CLASSES or
                    key == 'property' and value in PROPERTIES
                    for key, value in attrs.iteritems()))

    def process(self, response):
        strainer = SoupStrainer(self._strain_filter)
        soup = BeautifulSoup(response.text, parse_only=strainer)
        soup = soup.find_all(True, recursive=False)
        data = {}
        data['link'] = response.url

        for tag in soup:
            # By Name
            if tag.name == 'meta' and tag.has_key('property') and tag['property'] == 'og:image':
                if tag.has_key('content'):
                    data['thumbnail_url'] = tag['content']
                    continue
            elif tag.name == 'title':
                end_index = tag.string.find(" //")
                if end_index > -1:
                    data['title'] = unicode(tag.string[:end_index]).strip()
                    continue

            # By ID
            if tag.has_key('id'):
                if tag['id'] == 'slides_container':
                    data['embed_code'] = SpeakerDeckSuite.fix_script_embed_code(unicode(tag.script))
                    data['guid'] = SpeakerDeckSuite.build_guid(tag.script['data-id'])
                    continue
                elif tag['id'] == 'share_pdf':
                    data['file_url'] = unicode(tag['href'])
                    data['file_format'] = 'pdf'  # Always PDF
                    continue

            # By Class
            if tag.has_key('class'):
                if 'description' in tag['class']:
                    data['description'] = ''.join(unicode(item) for item in tag.contents)
                    continue
                elif 'presenter' in tag['class']:
                    data['user'] = unicode(tag.h2.a.string)
                    data['user_url'] = urljoin(response.url, tag.h2.a['href'])
                    continue

#        pprint(data)
        return data


class SpeakerDeckSuite(BaseSuite):
    """
    Suite for speakerdeck.com. Supports oEmbed and scraping (no API available).
    """
    provider_name = 'Speaker Deck'
    slide_regex = r'https?://([^/]+\.)?speakerdeck.com/u/(?P<username>\w+)/p/(?P<presentation_slug>\w+)'\
    # Example URLs:
    #    https://speakerdeck.com/u/kidpollo/p/tanker

    feed_regex = r'https?://([^/]+\.)?speakerdeck.com/u/(?P<username>\w+)(/?|(.atom)?)'
    # Example URLs:
    #    https://speakerdeck.com/u/holman.atom

    methods = (SpeakerDeckOEmbedMethod(u"https://speakerdeck.com/oembed.json"),
               SpeakerDeckScrapeMethod(),)

    @classmethod
    def build_guid(cls, speakerdeck_id):
        return u"speakerdeck-%s" % speakerdeck_id

#    @classmethod
#    def build_iframe_embed_code(cls, speakerdeck_id):
#        return "<iframe style=\"border:0; padding:0; margin:0; background:transparent;\" mozallowfullscreen=\"true\" webkitallowfullscreen=\"true\" frameBorder=\"0\" allowTransparency=\"true\" id=\"presentation_frame_%s\" src=\"//speakerdeck.com/embed/%s\" width=\"710\" height=\"618\"></iframe>\n"\
#            % (speakerdeck_id, speakerdeck_id)

    @classmethod
    def fix_script_embed_code(cls, speakerdeck_embed_script):
        """
        Convert relative urls to absolute url for script source
        """
        return speakerdeck_embed_script.replace('src="/assets', 'src="//speakerdeck.com/assets')

    # ATOM FEED METHODS
    def get_feed_url(self, feed_url, feed=None):
        if not feed_url.endswith('.atom'):
            if feed_url.endswith('/'):
                return '%s.atom' % feed_url[:-1]
            return '%s.atom' % feed_url
        return feed_url

    def parse_feed_entry(self, entry):
        soup = BeautifulSoup(entry['summary'])
        for tag in soup.find_all("img", limit=1):
            thumbnail_url = tag['src']
            print thumbnail_url
        for tag in soup.find_all("div", limit=1):
            description = ''.join(unicode(item) for item in tag.contents)
            print description

        id_start = entry['id'].rfind('/') + 1
        speakerdeck_id = entry['id'][id_start:]

        data = {
            'link': entry['link'],
            'title': entry['title'],
            'description': description,
            'thumbnail_url': thumbnail_url,
            'publish_datetime': struct_time_to_datetime(entry['published_parsed']),
            'user': entry['author'],
            'guid' : SpeakerDeckSuite.build_guid(speakerdeck_id),
        }
        return data

registry.register(SpeakerDeckSuite)

