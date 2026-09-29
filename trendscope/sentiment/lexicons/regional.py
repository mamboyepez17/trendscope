"""Jerga regional por país: se activa según el país del análisis (geo).

Solo palabras claras en ese país; lo ambiguo se deja fuera. Añadir un país es
agregar una entrada aquí (o usar CUSTOM_LEXICON_PATH con un JSON propio).
"""

REGIONAL: dict[str, dict[str, set[str]]] = {
    # Colombia
    "CO": {
        "joy": {"chimba", "berraquera", "melo", "bacano", "bacana", "que nota"},
        "anger": {
            "hp", "hijueputa", "malparid", "gonorrea", "piedra", "emberracad",
            "jarto", "jarta", "hartera", "careverga",
        },
        "sadness": {"guayabo", "achicopal", "aburrid"},
    },
    # México
    "MX": {
        "joy": {"chido", "chida", "chingon", "chingona", "padrisim", "chulo", "chula", "poca madre"},
        "anger": {"pinche", "cabron", "encabronad", "chale", "naco", "chafa", "culero"},
        "sadness": {"agüitad", "aguitad", "achicopal"},
    },
    # Argentina / Uruguay
    "AR": {
        "joy": {"copado", "copada", "genio", "groso", "grosa", "barbaro"},
        "anger": {"boludo", "boluda", "pelotud", "forro", "garca", "garcas", "quilombo", "chanta"},
        "sadness": {"bajon"},
    },
    "UY": {
        "joy": {"copado", "copada", "barbaro"},
        "anger": {"boludo", "pelotud", "garca"},
        "sadness": {"bajon"},
    },
    # Chile
    "CL": {
        "joy": {"filete", "choro", "chora", "bacan", "la raja"},
        "anger": {"chucha", "conchetumare", "chanta"},
        "sadness": {"fome", "bajon"},
    },
    # Perú
    "PE": {
        "joy": {"paja", "chevere", "bacan"},
        "anger": {"huevada", "cojudo", "cojuda"},
        "sadness": {"roche"},
    },
    # Venezuela
    "VE": {
        "joy": {"chevere"},
        "intensifiers": {"burda"},
        "anger": {"arrecho", "arrecha", "ladilla", "ladillad"},
    },
    # España
    "ES": {
        "joy": {"guay", "mola", "molan", "flipante", "flipo"},
        "anger": {"cabreo", "cabread", "gilipollas", "capullo", "chungo", "cutre"},
    },
    # Brasil
    "BR": {
        "joy": {"massa", "show", "maneiro", "top"},
        "anger": {"puto", "puta", "porra", "bosta", "zoado", "otario", "saco cheio"},
        "sadness": {"deprê", "depre", "bad"},
    },
    # Estados Unidos (jerga de internet)
    "US": {
        "joy": {"lit", "goated", "slay", "based"},
        "anger": {"mid", "cringe", "trash"},
    },
}
