# Copyright 2009 - Participatory Culture Foundation
# 
# This file is part of vidscraper.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
# IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
# OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
# NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
# THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import json
import datetime

from slidescraper.exceptions import UnhandledURL, SlidesDeleted
#from slidescraper.utils.search import (search_string_from_terms,
#                                       terms_from_search_string)


class Slides(object):
    """
    This is the class which should be used to represent slides which are
    returned by suite scraping, searching and feed parsing.

    :param url:   The url for the slide deck.
    :param suite: The suite to use for the slide deck. 
                  Does not need to be a registered suite, but does need to handle the given ``url``. 
                  If no suite is provided, one will be auto-selected based on the ``url``.
    :param fields: A list of fields which should be fetched for the slide show. 
                   This may be used to optimize the fetching process.

    """
    # FIELDS
    _all_fields = (
        'title', 'description', 'publish_datetime', 
        'link', 'embed_code', 'thumbnail_url',
        'language', 'view_count', 'slide_count', 'license_url',
        'file_url', 'file_format',
        'user', 'user_url', 'tags',  'guid',
        'index', 'provider'
    )
    #: The canonical link to the slideshow. This may not be the same as the url
    #: used to initialize the slideshow.
    link = None
    #: A (supposedly) global identifier for the slideshow
    guid = None
    #: Where the slideshow was in the feed/search
    index = None
    #: The slideshow's title.
    title = None
    #: A text or html description of the slideshow.
    description = None
    #: A python datetime indicating when the slideshow was published.
    publish_datetime = None
    #: The url to the actual slideshow download file.
    file_url = None
    #: The format for the slideshow download file
    file_format = None
#    #: The length of the actual video file
#    file_url_length = None
#    #: a datetime.datetime() representing when we think the file URL is no
#    #: longer valid
#    file_url_expires = None
    #: The actual embed code which can be used for displaying the video in a
    #: browser.
    embed_code = None
    #: The url for a thumbnail of the video.
    thumbnail_url = None
    #: The username associated with the video.
    user = None
    #: The url associated with the video's user.
    user_url = None
    #: A list of tag names associated with the video.
    tags = None
    #: A URL to a description of the license the Video is under (often Creative
    #: Commons)
    license_url = None
    #: Number of times the video has been viewed
    view_count = None
    #: The name of the video hosting provider
    provider = None
    
    language = None
    slide_count = None

    # These were pretty suite-specific and should perhaps be treated as such?
    #: Whether the video is embeddable? (Youtube, Vimeo)
    is_embeddable = None

    # OTHER ATTRS
    #: The url for this video to scrape based on.
    url = None
    #: An iterable of fields to be fetched for this video. Other fields will
    #: not populated during scraping.
    fields = None

    def __init__(self, url, suite=None, fields=None, api_keys=None):
        from slidescraper.suites import registry
        if suite is None:
            suite = registry.suite_for_slide_url(url)
        elif not suite.handles_slide_url(url):
            raise UnhandledURL
        if fields is None:
            self.fields = list(self._all_fields)
        else:
            self.fields = [f for f in fields if f in self._all_fields]
        self.url = url
        self._suite = suite
        self.api_keys = api_keys if api_keys is not None else {}
        self.provider = suite.provider_name if suite else None

        # This private attribute is set to ``True`` when data is loaded into
        # the slideshow by a scrape suite. It is *not* set when data is pre-loaded
        # from a feed or a search.
        self._loaded = False

    @property
    def missing_fields(self):
        """
        Returns a list of fields which have been requested but which have not
        been filled with data.

        """
        return [f for f in self.fields if getattr(self, f) is None]

    @property
    def suite(self):
        """The suite to be used for scraping this slide deck."""
        return self._suite

    def load(self):
        """Uses the slideshow's :attr:`suite` to fetch the fields for the slideshow."""
        if not self._loaded:
            data = self.suite.run_methods(self)
            self._apply(data)
            self._loaded = True

    def _apply(self, data):
        """
        Stores values from a ``data`` dictionary in the corresponding fields
        on this instance.
        """
        fields = set(data) & set(self.fields)
        for field in fields:
            setattr(self, field, data[field])

    def is_loaded(self):
        return self._loaded

    def items(self):
        """Iterator over (field, value) for requested fields."""
        for mem in self.fields:
            yield (mem, getattr(self, mem))

    def to_json(self, **kw):
        """Returns the slideshow JSON-ified.

        Takes keyword arguments and passes them to json.dumps().

        Example:

        >>> v.to_json(indent=2, sort_keys=True)
        """
        def json_dump_helper(obj):
            if isinstance(obj, datetime.datetime):
                return obj.isoformat()
            raise TypeError("%r is not serializable" % (obj,))

        kw['default'] = json_dump_helper
        return json.dumps(dict(self.items()), **kw)


class BaseSlideIterator(object):
    """
    Generic base class for url-based iterators which rely on suites to yield
    :class:`Slides` instances. :class:`SlideFeed` and
    :class:`SlideSearch` both subclass :class:`BaseSlideIterator`.
    """
    _first_response = None
    _max_results = None

    @property
    def max_results(self):
        """
        The maximum number of results for this iterator, or ``None`` if there
        is no maximum.

        """
        return self._max_results

    def get_first_url(self):
        """
        Returns the first url which this iterator is expected to handle.
        """
        raise NotImplementedError

    def get_url_response(self, url):
        raise NotImplementedError

    def handle_first_response(self, response):
        self._first_response = response 

    def get_response_items(self, response):
        raise NotImplementedError

    def get_item_data(self, item):
        raise NotImplementedError

    def get_next_url(self, response):
        raise NotImplementedError

    def load(self):
        if self._first_response:
            return self._first_response
        url = self.get_first_url()
        response = self.get_url_response(url)
        self.handle_first_response(response)
        return response

    def _data_from_item(self, item):
        """
        Returns a :class:`Slides` given some data from a feed.
        """
        data = self.get_item_data(item)
        slides = self.suite.get_slides(data['link'],
                                     fields=self.fields,
                                     api_keys=self.api_keys)
        slides._apply(data)
        slides.load()  # Fill in missing data from alternate methods
        return slides

    def __iter__(self):
        try:
            response = self.load()
            item_count = 1
            # decrease the index as we count down through the entries.  doesn't
            # quite work for feeds where we don't know the /total/ number of
            # items; then it'll just index the slides within the one feed
            while self._max_results is None or item_count < self._max_results:
                items = self.get_response_items(response)
                for item in items:
                    try:
                        slides = self._data_from_item(item)
                    except SlidesDeleted:
                        continue
                    slides.index = item_count
                    yield slides
                    if self._max_results is not None:
                        if item_count >= self._max_results:
                            raise StopIteration
                    item_count += 1

                # We haven't hit the limit yet. Continue to the next page if:
                # - crawl is enabled
                # - the current page was not empty
                # - a url can be calculated for the next page.
                url = None
                if self.crawl and items:
                    url = self.get_next_url(response)
                if url is None:
                    break
                response = self.get_url_response(url)
        except NotImplementedError:
            pass
        raise StopIteration


class SlideFeed(BaseSlideIterator):
    """
    Represents a feed that has been scraped from a website. Note that the term
    "feed" in this context simply means a list of slides which can be found at
    a certain url. The source could as easily be an API, a search result rss
    feed, or a list page which is literally scraped.
    
    :param url: The url to be scraped.
    :param suite: The suite to use for the scraping. If none is provided, one
                  will be selected based on the url.
    :param fields: Passed on to the :class:`Slides` instances which are
                   created by this feed.
    :param crawl: If ``True``, then the scrape will continue onto subsequent
                  pages of the feed if that is supported by the suite. The
                  request for the next page will only be executed once the
                  current page is exhausted. Default: ``False``.
    :param max_results: The maximum number of results to return from iteration.
                        Default: ``None`` (as many as possible.)
    :param api_keys: A dictionary of any API keys which may be required for the
                     suite used by this feed.
    :param last_modified: A last-modified date which may be sent to the service
                          provider to try to short-circuit fetching a feed
                          whose contents are already known.
    :param etag: An etag which may be sent to the service provider to try to
                 short-circuit fetching a feed whose contents are already
                 known.

    Additionally, :class:`SlideFeed` populates the following attributes after
    fetching its first response. Attributes which are not supported by the
    feed's suite or which have not been populated will be ``None``.

    .. attribute:: entry_count

       The estimated number of entries for this search.

    .. attribute:: last_modified

       A python datetime representing when the feed was last changed. Before
       fetching the first response, this will be equal to the
       ``last_modified`` date the :class:`SlideFeed` was instantiated with.

    .. attribute:: etag

       A marker representing a feed's current state. Before fetching the first
       response, this will be equal to the ``etag`` the :class:`SlideFeed`
       was instantiated with.

    .. attribute:: description

       A description of the feed.

    .. attribute:: webpage

       The url for an html, human-readable version of the feed.

    .. attribute:: title

       The title of the feed.

    .. attribute:: thumbnail_url

       A URL for a thumbnail representing the whole feed.

    .. attribute:: guid

       A unique identifier for the feed.

    """

    def __init__(self, url, suite=None, fields=None, crawl=False,
                 max_results=None, api_keys=None, last_modified=None,
                 etag=None):
        from slidescraper.suites import registry
        self.original_url = url
        if suite is None:
            suite = registry.suite_for_feed_url(url)
        elif not suite.handles_feed_url(url):
            raise UnhandledURL
        self.suite = suite
        self.fields = fields
        self.crawl = crawl
        self._max_results = max_results
        self.api_keys = api_keys if api_keys is not None else {}
        self.url = suite.get_feed_url(url, feed=self)
        self.last_modified = last_modified
        self.etag = etag

        self.entry_count = None
        self.description = None
        self.webpage = None
        self.title = None
        self.thumbnail_url = None
        self.guid = None

    @property
    def parsed_feed(self):
        if not self._first_response:
            self.load()
        return self._first_response

    def get_first_url(self):
        return self.url

    def get_url_response(self, url):
        return self.suite.get_feed_response(self, url)

    def handle_first_response(self, response):
        super(SlideFeed, self).handle_first_response(response)
        response = self.suite.get_feed_info_response(self, response)
        self.title = self.suite.get_feed_title(self, response)
        self.entry_count = self.suite.get_feed_entry_count(self, response)
        self.description = self.suite.get_feed_description(self, response)
        self.webpage = self.suite.get_feed_webpage(self, response)
        self.thumbnail_url = self.suite.get_feed_thumbnail_url(self, response)
        self.guid = self.suite.get_feed_guid(self, response)
        self.last_modified = self.suite.get_feed_last_modified(self, response)
        self.etag = self.suite.get_feed_etag(self, response)

    def get_response_items(self, response):
        return self.suite.get_feed_entries(self, response)

    def get_item_data(self, item):
        return self.suite.parse_feed_entry(item)

    def get_next_url(self, response):
        return self.suite.get_next_feed_page_url(self, response)


#class SlideSearch(BaseSlideIterator):
#    """
#    Represents a search against a suite. Iterating over a
#    :class:`SlideSearch` instance will execute the search and yield
#    :class:`Slides` instances for the results of the search.
#
#    :param query: The raw string for the search.
#    :param suite: Suite to use for this search.
#    :param fields: Passed on to the :class:`Slides` instances which are
#                   created by this search.
#    :param order_by: The ordering to apply to the search results. If a suite
#                     does not support the given ordering, it will return an
#                     empty list. Possible values: ``relevant``, ``latest``,
#                     ``popular``, ``None`` (use the default ordering of the
#                     suite's service provider). Values may be prefixed with a
#                     "-" to indicate descending ordering. Default: ``None``.
#    :param crawl: If ``True``, then the search will continue on to subsequent
#                  pages if the suite supports it. The request for the next page
#                  will only be executed once the current page is exhausted.
#                  Default: ``False``.
#    :param max_results: The maximum number of results to return from iteration.
#                        Default: ``None`` (as many as possible).
#    :param api_keys: A dictionary of any API keys which may be required for the
#                     suite used by this search.
#
#    Additionally, SlideSearch supports the following attributes:
#
#    .. attribute:: total_results
#
#       The estimated number of total results for this search, if supported by
#       the suite. Otherwise, ``None``.
#
#    .. attribute:: time
#
#       The amount of time required by the remote service to execute the query,
#       if supported by the suite. Otherwise, ``None``.
#
#    """
#
#    @property
#    def max_results(self):
#        return self._max_results
#
#    def __init__(self, query, suite, fields=None, order_by=None,
#                 crawl=False, max_results=None, api_keys=None):
#        self.include_terms, self.exclude_terms = terms_from_search_string(
#            query)
#        self.query = search_string_from_terms(self.include_terms,
#                                              self.exclude_terms)
#        self.raw_query = query
#        self.suite = suite
#        self.fields = fields
#        self.order_by = order_by
#        self.crawl = crawl
#        self._max_results = max_results
#        self.api_keys = api_keys if api_keys is not None else {}
#
#        self.total_results = None
#        self.time = None
#
#    def get_first_url(self):
#        return self.suite.get_search_url(self)
#
#    def get_url_response(self, url):
#        return self.suite.get_search_response(self, url)
#
#    def handle_first_response(self, response):
#        super(SlideSearch, self).handle_first_response(response)
#        self.total_results = self.suite.get_search_total_results(self,
#                                                                 response)
#        self.time = self.suite.get_search_time(self, response)
#
#    def get_response_items(self, response):
#        return self.suite.get_search_results(self, response)
#
#    def get_item_data(self, item):
#        return self.suite.parse_search_result(self, item)
#
#    def get_next_url(self, response):
#        return self.suite.get_next_search_page_url(self, response)
