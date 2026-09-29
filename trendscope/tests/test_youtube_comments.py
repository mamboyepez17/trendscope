"""Comentarios de YouTube (innertube /next): token, ambos formatos, recolector."""

from unittest.mock import MagicMock, patch

from trendscope.core.query import TrendQuery
from trendscope.scrapers import youtube

WATCH = {
    "contents": {"twoColumnWatchNextResults": {"results": {"results": {"contents": [
        {"videoPrimaryInfoRenderer": {}},
        {"itemSectionRenderer": {
            "sectionIdentifier": "comment-item-section",
            "contents": [{"continuationItemRenderer": {"continuationEndpoint": {
                "continuationCommand": {"token": "TOKEN123"}}}}],
        }},
    ]}}}}
}

NEW_FORMAT = {
    "onResponseReceivedEndpoints": [{"reloadContinuationItemsCommand": {"continuationItems": [
        {"commentThreadRenderer": {"commentViewModel": {"commentViewModel": {"commentKey": "k1"}}}},
    ]}}],
    "frameworkUpdates": {"entityBatchUpdate": {"mutations": [
        {"payload": {"commentEntityPayload": {
            "key": "k1",
            "properties": {"commentId": "Ugx1", "content": {"content": "Qué rabia con esta reforma 😡"},
                           "publishedTime": "hace 2 horas"},
            "author": {"displayName": "@ana"},
            "toolbar": {"likeCountNotliked": "1,2 mil"},
        }}},
    ]}},
}

OLD_FORMAT = {
    "onResponseReceivedEndpoints": [{"appendContinuationItemsAction": {"continuationItems": [
        {"commentThreadRenderer": {"comment": {"commentRenderer": {
            "commentId": "Ugx2",
            "contentText": {"runs": [{"text": "Me encanta, "}, {"text": "por fin!"}]},
            "authorText": {"simpleText": "@leo"},
            "voteCount": {"simpleText": "15"},
            "publishedTimeText": {"runs": [{"text": "3 days ago"}]},
        }}}},
    ]}}],
}

VIDEO = {"video_id": "abc", "url": "https://www.youtube.com/watch?v=abc", "title": "Reforma a la salud hoy"}


def test_comments_token_found():
    assert youtube._comments_token(WATCH) == "TOKEN123"
    assert youtube._comments_token({"contents": {}}) is None


def test_parse_new_entity_format():
    out = youtube.parse_comments_payload(NEW_FORMAT, VIDEO)
    assert len(out) == 1
    c = out[0]
    assert c["source"] == "youtube_comment" and c["kind"] == "comment"
    assert c["text"].startswith("Qué rabia")
    assert c["author"] == "ana" and c["likes"] == 1200
    assert c["created_utc"] and c["permalink"].endswith("&lc=Ugx1")


def test_parse_old_renderer_format():
    out = youtube.parse_comments_payload(OLD_FORMAT, VIDEO)
    assert [c["text"] for c in out] == ["Me encanta, por fin!"]
    assert out[0]["likes"] == 15 and out[0]["author"] == "leo"


def test_fetch_video_comments_two_calls():
    r1, r2 = MagicMock(), MagicMock()
    r1.json.return_value, r2.json.return_value = WATCH, NEW_FORMAT
    with patch("trendscope.scrapers.youtube.requests.post", side_effect=[r1, r2]) as post:
        out = youtube.fetch_video_comments(VIDEO, geo="MX")
    assert len(out) == 1
    assert post.call_args_list[1].kwargs["json"]["continuation"] == "TOKEN123"
    # Idioma/país del cliente según el país pedido (no fijo en CO)
    assert post.call_args_list[0].kwargs["json"]["context"]["client"]["gl"] == "MX"


def test_collect_comments_only_relevant_videos():
    videos = [
        {**VIDEO, "views": 10},
        {"video_id": "zzz", "url": "u", "title": "Tutorial de cocina", "views": 999},
    ]
    with patch("trendscope.scrapers.youtube._search_youtube", return_value=videos):
        with patch("trendscope.scrapers.youtube.fetch_video_comments", return_value=[{"text": "x"}]) as f:
            with patch("trendscope.scrapers.youtube.time.sleep"):
                vids, comments = youtube.collect_comments(
                    TrendQuery(mode="free", free_topic="reforma a la salud"))
    assert [v["video_id"] for v in vids] == ["abc"]
    f.assert_called_once()
