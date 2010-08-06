from xml.sax.saxutils import escape
from django.core.paginator import Paginator, EmptyPage, InvalidPage
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404

from molly.utils.views import BaseView
from molly.utils.breadcrumbs import *

from ..models import Feed, Item

class IndexView(BaseView):
    def get_metadata(cls, request):
        return {
            'title': 'News',
            'additional': 'View news feeds and events from across the University.',
        }
        
    @BreadcrumbFactory
    def breadcrumb(cls, request, context):
        return Breadcrumb(
            cls.conf.local_name, None, 'News', lazy_reverse('news:index')
        )
        
    def handle_GET(cls, request, context):
        feeds = Feed.news.all()
        context['feeds'] = feeds
        return cls.render(request, context, 'rss/news/index')

class ItemListView(BaseView):
    def get_metadata(cls, request, slug):
        feed = get_object_or_404(Feed.news, slug=slug)
        
        last_modified = feed.last_modified.strftime('%a, %d %b %Y') if feed.last_modified else 'never updated'
        return {
            'last_modified': feed.last_modified,
            'title': feed.title,
            'additional': '<strong>News feed</strong>, %s' % last_modified,
        }

    @BreadcrumbFactory
    def breadcrumb(cls, request, context, slug):
        return Breadcrumb(
            cls.conf.local_name,
            lazy_parent(IndexView),
            'News feed',
            lazy_reverse('news:item_list', args=[slug])
        )
        
    def handle_GET(cls, request, context, slug):
        feed = get_object_or_404(Feed.news, slug=slug)
        context['feed'] = feed
        return cls.render(request, context, 'rss/news/item_list')

class ItemDetailView(BaseView):
    def get_metadata(cls, request, slug, id):
        item = get_object_or_404(Item, feed__slug=slug, id=id)
        
        last_modified = item.last_modified.strftime('%a, %d %b %Y') if item.last_modified else 'never updated'
        return {
            'last_modified': item.last_modified,
            'title': item.title,
            'additional': '<strong>News item</strong>, %s, %s' % (escape(item.feed.title), last_modified),
        }

    @BreadcrumbFactory
    def breadcrumb(cls, request, context, slug, id):
        return Breadcrumb(
            cls.conf.local_name,
            lazy_parent(ItemListView, slug=slug),
            'News item',
            lazy_reverse('news:item_detail', args=[slug,id])
        )
        
    def handle_GET(cls, request, context, slug, id):
        item = get_object_or_404(Item, feed__slug=slug, id=id)
        context.update({
            'item': item,
            'description': item.get_description_display(request.device)
        })
        return cls.render(request, context, 'rss/news/item_detail')
