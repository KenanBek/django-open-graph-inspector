import urllib2
import urlparse

from bs4 import BeautifulSoup
import chardet
from django.db.models import Q
from django.shortcuts import get_object_or_404

from core import abstracts
from . import models


class BlogLogic(abstracts.LogicAbstract):
    def __init__(self, request):
        super(BlogLogic, self).__init__(request)

    def page(self, page_slug):
        return get_object_or_404(models.Page, slug=page_slug, status=models.ITEM_STATUS_PUBLISHED)

    def pages(self, page_number=None):
        return models.Page.objects.filter(status=models.ITEM_STATUS_PUBLISHED).all()

    def post(self, post_id, post_slug):
        return get_object_or_404(models.Post, pk=post_id, slug=post_slug, status=models.ITEM_STATUS_PUBLISHED)

    def posts(self, page_number=None):
        return models.Post.objects.filter(status=models.ITEM_STATUS_PUBLISHED).order_by('-modified_at').all()

    def search(self, term):
        pages = models.Page.objects.filter(Q(title__contains=term) | Q(content__contains=term))
        posts = models.Post.objects.filter((Q(title__contains=term)
                                            | Q(short_content__contains=term)
                                            | Q(full_content__contains=term))
                                           & Q(status=models.ITEM_STATUS_PUBLISHED))
        return {
            "pages": pages,
            "posts": posts
        }

    def new_subscription(self, name, email):
        subscriber = models.Subscriber()
        subscriber.name = name
        subscriber.email = email
        subscriber.save()


''' The Open Graph Protocol '''


class WebPage(object):
    def __init__(self, success=None, content=None, status=None, message=None):
        self.success = success
        self.status = status
        self.message = message
        self.content = content


class WebInspector(object):
    def __init__(self, success=None, web_link=None, message=None):
        self.success = success
        self.web_link = web_link
        self.message = message


class Helper(object):
    @staticmethod
    def to_unicode_or_bust(obj):
        if isinstance(obj, basestring):
            if not isinstance(obj, unicode):
                success = True
                try:
                    obj = unicode(obj, 'utf-8')
                except:
                    success = False
                if not success:
                    try:
                        encoding = chardet.detect(obj)
                        if encoding:
                            encoding_text = encoding.get('encoding', None)
                            if encoding_text:
                                obj = unicode(obj).decode(encoding_text).encode('utf-8')
                    except:
                        pass
                        # try:
                        # obj = unicode(obj).decode('latin1').encode('utf-8')
                        # except:
                        # pass
                        # try:
                        # encoding = chardet.detect(obj).encoding
                        # obj = unicode(obj).decode(encoding).encode('utf-8')
                        # except:
                        # pass
        return obj

    @staticmethod
    def get_page_by_url(url):
        try:
            encoded_url = Helper.to_unicode_or_bust(url)
            request = urllib2.Request(url=encoded_url, headers={'User-Agent': "Mozilla/5.0 (Windows NT 6.2; WOW64)"})
            page_stream = urllib2.urlopen(request, timeout=5)
            if page_stream.url != encoded_url:
                message = u"redirect to {}".format(page_stream.url)
                return WebPage(success=False, message=message)
            else:
                content = page_stream.read()
                encoded_content = Helper.to_unicode_or_bust(content)
                return WebPage(success=True, status=page_stream.code, content=encoded_content)
        except urllib2.HTTPError as e:
            return WebPage(success=False, status=e.code, message=e.msg)
        except Exception as e:
            return WebPage(success=False, message=repr(e))

    @staticmethod
    def clean_array(seq):
        seen = set()
        seen_add = seen.add
        return [x for x in seq if not (x in seen or seen_add(x))]

    @staticmethod
    def get_domain(url):
        parsed_uri = urlparse.urlparse(url)
        domain = '{uri.scheme}://{uri.netloc}/'.format(uri=parsed_uri)
        return domain

    @staticmethod
    def fix_url(parent_url, url):
        # parsed_uri = urlparse.urlparse(parent_url)
        # domain = '{uri.scheme}://{uri.netloc}/'.format(uri=parsed_uri)
        result = urlparse.urljoin(parent_url, url)
        return result


class OpenGraphLogic(object):
    url = None

    def __init__(self, url):
        self.url = Helper.to_unicode_or_bust(url)

    def _get_web_link(self):
        web_link = models.WebLink()
        web_link.url = self.url
        web_links = models.WebLink.objects.filter(url=self.url).order_by('-version').all()
        if web_links.count():
            self.version = web_links[0].version + 1
        else:
            self.version = 1
        web_link.version = self.version
        return web_link

    def _css_select(self, document, selector):
        return document.select(selector)

    def _get_text_tag_value(self, document, selector):
        tag = self._css_select(document, selector)
        if tag:
            return Helper.to_unicode_or_bust(tag[0].text)

    def _get_meta_tag_value(self, document, selector):
        tag = self._css_select(document, selector)
        if tag:
            content = tag[0].get('content', None)
            return Helper.to_unicode_or_bust(content)

    def _get_og_image_urls(self, document):
        result = []
        tags = self._css_select(document, 'meta[property=og:image]')
        if tags:
            for tag in tags:
                url = tag.get('content', None)
                if url:
                    result.append(Helper.to_unicode_or_bust(url))
        return Helper.clean_array(result)

    def _get_html_image_urls(self, document):
        result = []
        tags = self._css_select(document, 'img')
        if tags:
            for tag in tags:
                url = tag.get('src', None)
                if url:
                    result.append(Helper.to_unicode_or_bust(url))
        return Helper.clean_array(result)

    def inspect(self):
        result = WebInspector()
        page_loader = Helper.get_page_by_url(self.url)
        if page_loader.success:
            try:
                content = page_loader.content
                document = BeautifulSoup(content)
                web_link = self._get_web_link()
                web_link.title = self._get_text_tag_value(document, 'title')
                web_link.description = self._get_meta_tag_value(document, 'meta[name=description]')
                web_link.keywords = self._get_meta_tag_value(document, 'meta[name=keywords]')
                web_link.author = self._get_meta_tag_value(document, 'meta[name=author]')

                web_link.og_title = self._get_meta_tag_value(document, 'meta[property=og:title]')
                web_link.og_url = self._get_meta_tag_value(document, 'meta[property=og:url]')
                web_link.og_type = self._get_meta_tag_value(document, 'meta[property=og:type]')
                web_link.og_image = self._get_meta_tag_value(document, 'meta[property=og:image]')
                web_link.og_description = self._get_meta_tag_value(document, 'meta[property=og:description]')
                web_link.og_site_name = self._get_meta_tag_value(document, 'meta[property=og:site_name]')

                web_link.save()
                parent_url = self.url

                og_image_urls = self._get_og_image_urls(document)
                for image_url in og_image_urls:
                    web_image = models.WebImage()
                    web_image.image_url = Helper.fix_url(parent_url, image_url)
                    web_image.web_link = web_link
                    web_image.save()

                html_image_urls = self._get_html_image_urls(document)
                for image_url in html_image_urls:
                    web_image = models.WebImage()
                    web_image.image_url = Helper.fix_url(parent_url, image_url)
                    web_image.web_link = web_link
                    web_image.save()

                result.success = True
                result.web_link = web_link
            except Exception as e:
                message = u"Exception on inspection url '{}': {}".format(self.url, repr(e))
                result.success = False
                result.message = message
        else:
            result.success = False
            result.message = page_loader.message
        return result

