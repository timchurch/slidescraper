from slidescraper.suites import BaseSuite, registry, SuiteMethod, OEmbedMethod
import json


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


class SpeakerDeckSuite(BaseSuite):
    """
    Suite for speakerdeck.com. Currently only supports oembed.
    """
    provider_name = 'Speaker Deck'
    slide_regex = r'https?://([^/]+\.)?speakerdeck.com/u/(?P<username>\w+)/p/(?P<presentation_slug>\w+)'

    methods = (SpeakerDeckOEmbedMethod(u"https://speakerdeck.com/oembed.json"),)
registry.register(SpeakerDeckSuite)