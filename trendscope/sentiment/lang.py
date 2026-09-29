"""Detección ligera de idioma por palabras vacías y letras propias.

Cubre es, en, pt, fr, de, it (los idiomas con léxico). Si el texto es muy
corto o ambiguo devuelve el idioma por defecto (el del país del análisis).
"""

from __future__ import annotations

import re

_STOP = {
    "es": set("el la los las un una unos de del en es que por para con como pero mas este esta "
              "son fue ser tiene hay muy tambien sobre porque aunque cuando donde yo usted ellos "
              "nosotros esto eso ya se lo le nos mi".split()),
    "en": set("the and is are was were this that with for from have has will can about you they "
              "we it's its not but what who how just been would there their".split()),
    "pt": set("o os as um uma de do da dos das em no na que por para com como mas este esta isso "
              "nao sao foi ser tem muito tambem sobre porque quando onde eu voce eles nos ja se "
              "lhe meu minha ele ela".split()),
    "fr": set("le la les un une des de du en est que pour dans avec sur pas je vous nous ils elle "
              "ce cette c'est mais tres aussi comme qui au aux ne ont sont".split()),
    "de": set("der die das und ist nicht ich ein eine zu mit auf sie es den dem des von wir ihr "
              "auch aber wie was wenn noch nur sehr sind hat".split()),
    "it": set("il lo la gli le un una di del della che non per con come ma questo questa sono "
              "anche molto io tu lui lei noi voi loro gia se mi ti ci perche quando".split()),
}

# Letras que casi solo aparecen en un idioma
_CHAR_HINTS = {
    "es": "ñ¿¡",
    "pt": "ãõ",
    "de": "ß",
    "fr": "œ",
}


def _strip(text: str) -> str:
    import unicodedata

    return "".join(
        c for c in unicodedata.normalize("NFD", text.lower()) if unicodedata.category(c) != "Mn"
    )


def detect(text: str, default: str = "es") -> str:
    raw = (text or "").lower()
    if len(raw.strip()) < 3:
        return default
    scores = {lang: 0.0 for lang in _STOP}
    for lang, chars in _CHAR_HINTS.items():
        if any(c in raw for c in chars):
            scores[lang] += 2.5
    words = re.findall(r"[a-z']+", _strip(raw))
    for w in words:
        for lang, stop in _STOP.items():
            if w in stop:
                scores[lang] += 1
    best = max(scores, key=scores.get)
    top = scores[best]
    if top < 1:
        return default
    # Empate con el idioma por defecto → el por defecto
    if scores.get(default, 0) >= top:
        return default
    return best
