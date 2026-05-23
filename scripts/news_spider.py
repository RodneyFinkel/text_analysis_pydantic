import scrapy
from urllib.parse import urlparse
from datetime import datetime
from dateutil import parser


class NewsCrawler(scrapy.Spider):
    name = "news_crawler"

    custom_settings = {
        "DEPTH_LIMIT": 3,
        "ROBOTSTXT_OBEY": True,
        "DOWNLOAD_DELAY": 0.5,
        "CONCURRENT_REQUESTS": 8,
    }

    def __init__(self, urls=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not urls:
            raise ValueError("Provide comma-separated URLs via -a urls=...")

        # multiple seeds
        self.start_urls = [u.strip() for u in urls.split(",")]

        # restrict domains automatically
        self.allowed_domains = list({
            urlparse(u).netloc for u in self.start_urls
        })

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(url, callback=self.parse, meta={"depth": 0})

    def parse(self, response):
        """
        Main dispatcher:
        - Extract article if page looks like one
        - Discover and follow links
        """

        if self.is_article(response):
            yield self.extract_article(response)

        # follow links
        for href in response.css("a::attr(href)").getall():
            url = response.urljoin(href)

            if self.should_follow(url):
                yield scrapy.Request(
                    url,
                    callback=self.parse,
                    dont_filter=False  # let Scrapy deduplicate
                )

    # ----------------------------
    # Heuristics
    # ----------------------------

    def is_article(self, response):
        """
        Heuristic classification of article pages
        """
        has_h1 = response.css("h1").get() is not None
        has_paragraphs = len(response.css("p")) > 5

        return has_h1 and has_paragraphs

    def should_follow(self, url):
        """
        Filter out irrelevant links
        """
        parsed = urlparse(url)

        if parsed.netloc not in self.allowed_domains:
            return False

        # exclude common non-content paths
        excluded = ["login", "signup", "account", "privacy", "terms"]
        if any(x in parsed.path.lower() for x in excluded):
            return False

        return True

    # ----------------------------
    # Extraction logic
    # ----------------------------

    def extract_article(self, response):
        title = (
            response.css("h1::text").get() or
            response.css('meta[property="og:title"]::attr(content)').get() or
            response.css("title::text").get()
        )

        raw_date = (
            response.css("time::attr(datetime)").get() or
            response.css('meta[property="article:published_time"]::attr(content)').get()
        )

        parsed_date = parser.parser.parse(raw_date).isoformat() if raw_date else None

        article = response.css("article")
        content = " ".join(
            article.css("p *::text, p::text").getall()
        ) if article else " ".join(response.css("p *::text, p::text").getall())

        return {
            "title": title,
            "url": response.url,
            "date": parsed_date,
            "content": content,
            "metadata": {
                "source": urlparse(response.url).netloc,
                "scrape_timestamp": datetime.utcnow().isoformat(),
            },
        }