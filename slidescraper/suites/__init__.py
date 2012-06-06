from slidescraper.suites.base import (registry, BaseSuite, SuiteMethod, OEmbedMethod)

# Force loading of these files so that the default suites get registered.
from slidescraper.suites import slideshare, speakerdeck