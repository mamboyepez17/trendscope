"""
XActions-PY — Query builder de búsqueda avanzada de X.

Operadores soportados (sintaxis nativa de X search):
  from:user  to:user  @user  #hashtag  "exact phrase"
  since:YYYY-MM-DD  until:YYYY-MM-DD
  min_faves:N  min_retweets:N  min_replies:N
  lang:es  filter:media  filter:verified  -filter:retweets  -filter:replies
  is:reply  is:quote  url:"example.com"
"""

from __future__ import annotations


def build_search_query(
    base: str = "",
    *,
    from_user: str | None = None,
    to_user: str | None = None,
    mention: str | None = None,
    hashtag: str | None = None,
    phrase: str | None = None,
    since: str | None = None,
    until: str | None = None,
    min_faves: int | None = None,
    min_retweets: int | None = None,
    min_replies: int | None = None,
    lang: str | None = None,
    filter_media: bool = False,
    filter_verified: bool = False,
    filter_links: bool = False,
    exclude_retweets: bool = False,
    exclude_replies: bool = False,
    is_reply: bool = False,
    is_quote: bool = False,
    url: str | None = None,
    extra: str | None = None,
) -> str:
    """
    Construye una query de búsqueda de X a partir de flags.

    Ejemplo:
        build_search_query(
            "crypto",
            from_user="elonmusk",
            min_faves=100,
            lang="es",
            exclude_retweets=True,
        )
        # → 'crypto from:elonmusk min_faves:100 lang:es -filter:retweets'
    """
    parts: list[str] = []

    if base and base.strip():
        parts.append(base.strip())

    def _user(u: str | None) -> str | None:
        if not u:
            return None
        return u.lstrip("@").strip() or None

    fu = _user(from_user)
    if fu:
        parts.append(f"from:{fu}")
    tu = _user(to_user)
    if tu:
        parts.append(f"to:{tu}")
    ment = _user(mention)
    if ment:
        parts.append(f"@{ment}")

    if hashtag:
        tag = hashtag.lstrip("#").strip()
        if tag:
            parts.append(f"#{tag}")
    if phrase:
        p = phrase.strip()
        if p:
            if not (p.startswith('"') and p.endswith('"')):
                p = f'"{p}"'
            parts.append(p)

    if since:
        parts.append(f"since:{since.strip()}")
    if until:
        parts.append(f"until:{until.strip()}")

    if min_faves is not None and min_faves >= 0:
        parts.append(f"min_faves:{int(min_faves)}")
    if min_retweets is not None and min_retweets >= 0:
        parts.append(f"min_retweets:{int(min_retweets)}")
    if min_replies is not None and min_replies >= 0:
        parts.append(f"min_replies:{int(min_replies)}")

    if lang:
        parts.append(f"lang:{lang.strip()}")
    if filter_media:
        parts.append("filter:media")
    if filter_verified:
        parts.append("filter:blue_verified")
    if filter_links:
        parts.append("filter:links")
    if exclude_retweets:
        parts.append("-filter:retweets")
    if exclude_replies:
        parts.append("-filter:replies")
    if is_reply:
        parts.append("is:reply")
    if is_quote:
        parts.append("is:quote")
    if url:
        u = url.strip()
        if " " in u:
            u = f'"{u}"'
        parts.append(f"url:{u}")

    if extra and extra.strip():
        parts.append(extra.strip())

    return " ".join(parts)
