from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from workbench.models import AudioSegment, Books, DialogueScript

from .models import DiscussionTopic


class StaticViewSitemap(Sitemap):
    changefreq = "daily"

    def items(self):
        return ["home", "explore", "about", "discussion_list"]

    def location(self, item):
        return reverse(item)

    def priority(self, item):
        return 1.0 if item == "home" else 0.6


class AudioSegmentSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return AudioSegment.objects.filter(published=True)

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse("audio_detail", kwargs={
            "segment_type": "audio_segment",
            "segment_id": obj.id,
        })


class DialogueScriptSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return DialogueScript.objects.filter(published=True, audio_file__isnull=False)

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse("audio_detail", kwargs={
            "segment_type": "dialogue_script",
            "segment_id": obj.id,
        })


class BookSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.6

    def items(self):
        # 只收录有已发布音频的书籍，避免空页面
        return Books.objects.filter(
            audio_segments__published=True,
        ).distinct()

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse("book_audio_list", kwargs={"book_id": obj.id})


class DiscussionTopicSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.5

    def items(self):
        return DiscussionTopic.objects.all()

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse("discussion_topic_detail", kwargs={"topic_id": obj.id})
