"""Léxicos base por idioma (sin tildes al compararse; se normalizan al cargar).

Reglas de escritura:
  - Palabras < 5 letras: solo coinciden como palabra completa.
  - Raíces ≥ 5 letras: coinciden como prefijo ("enojad" → enojado, enojada).
  - Evita palabras ambiguas en su idioma ("pena" en "vale la pena",
    "pesar" en "a pesar de", "solo" = only): generan falsos positivos.
"""

BASE: dict[str, dict[str, set[str]]] = {
    "es": {
        "joy": {
            "feliz", "felices", "felicidad", "alegr", "contento", "contenta", "contentos",
            "encant", "amo", "amor", "genial", "excelente", "increible", "maravill",
            "fantastic", "hermos", "brillante", "perfecto", "perfecta", "bueno", "buena",
            "buenisim", "gracias", "agradec", "orgull", "celebr", "felicit", "exito",
            "logro", "victoria", "gano", "ganamos", "bravo", "espectacular", "recomiend",
            "satisfech", "emocion", "ilusion", "esperanz", "disfrut", "chevere", "bacan",
            "brutal", "crack", "lindo", "linda", "divin", "jaja", "jajaja", "jeje", "xd",
        },
        "anger": {
            "enojad", "enoja", "rabia", "furios", "odio", "odia", "odiar", "odian",
            "indign", "harto", "harta", "cansad", "fastid", "molest", "asco", "asquer",
            "verguenza", "vergonz", "ladron", "ladrones", "rata", "ratas", "corrupt",
            "estafa", "estafador", "robo", "robar", "roban", "mentir", "mentiros",
            "mentira", "abuso", "pesimo", "pesima", "horrible", "terrible", "basura",
            "porqueria", "inutil", "incompetent", "descarad", "sinverguenz", "cinic",
            "burla", "exijo", "exigimos", "renuncie", "protest", "mierda", "maldit",
            "idiota", "imbecil", "estupid", "payaso", "bruto", "bruta",
        },
        "sadness": {
            "triste", "tristeza", "entristec", "lament", "llora", "lloro", "llorar",
            "llorando", "dolor", "duele", "doloros", "deprim", "depresion", "decepcion",
            "decepcionad", "desilusion", "desanim", "perdimos", "perdida", "luto",
            "fallec", "murio", "muerte", "tragedia", "tragic", "sufre", "sufrir",
            "sufriendo", "soledad", "desesper", "rip",
        },
        "fear": {
            "miedo", "temor", "asust", "susto", "panico", "aterr", "preocup", "angusti",
            "ansied", "ansios", "nervios", "insegur", "peligr", "riesgo", "amenaz",
            "alarm", "incertidumbre", "crisis", "colaps", "quiebra", "inflacion",
            "desempleo", "violencia",
        },
        "neg": {
            "malo", "mala", "malos", "malas", "mal", "peor", "peores", "fracaso",
            "fracas", "desastre", "error", "fallo", "falla", "problema", "caro",
            "carisimo", "lento",
        },
        "negations": {"no", "ni", "nunca", "jamas", "tampoco", "sin", "nada"},
        "intensifiers": {
            "muy", "demasiado", "super", "re", "tan", "tanto", "bastante", "sumamente",
            "extremadamente", "totalmente", "absolutamente", "completamente", "mega",
        },
    },
    "en": {
        "joy": {
            "happy", "glad", "love", "loved", "great", "awesome", "amazing", "excellent",
            "wonderful", "fantastic", "best", "good", "nice", "thanks", "thank", "proud",
            "excited", "enjoy", "beautiful", "perfect", "win", "winning", "lol", "haha",
            "yay", "congrat",
        },
        "anger": {
            "angry", "anger", "mad", "furious", "rage", "hate", "hated", "pissed",
            "annoy", "outrage", "disgust", "disgusting", "sick", "scam", "fraud", "liar",
            "lie", "lies", "corrupt", "awful", "worst", "trash", "garbage", "stupid",
            "idiot", "pathetic", "ridiculous", "wtf", "shame",
        },
        "sadness": {
            "sad", "sadly", "sadness", "cry", "crying", "tears", "heartbroken", "depress",
            "disappoint", "miss", "lonely", "grief", "tragic", "unfortunately", "sorry",
            "loss", "died", "death",
        },
        "fear": {
            "fear", "afraid", "scared", "scary", "terrified", "panic", "worried", "worry",
            "anxious", "anxiety", "nervous", "danger", "dangerous", "threat", "risk",
            "risky", "uncertain", "crisis", "collapse",
        },
        "neg": {
            "bad", "poor", "fail", "failure", "broken", "problem", "expensive", "slow",
            "sucks",
        },
        "negations": {
            "not", "never", "dont", "don", "isnt", "wasnt", "aint", "cant", "nobody",
            "without", "no",
        },
        "intensifiers": {"very", "so", "really", "extremely", "totally", "absolutely", "too"},
    },
    "pt": {
        "joy": {
            "feliz", "felicidade", "alegre", "alegria", "amo", "amei", "adoro", "otimo",
            "otima", "excelente", "maravilhos", "incrivel", "parabens", "obrigad",
            "sucesso", "vitoria", "lindo", "linda", "perfeito", "perfeita", "bom", "boa",
            "orgulho", "celebr", "esperanca", "kkkk", "kkkkk", "rsrs", "haha",
        },
        "anger": {
            "raiva", "odio", "odeio", "irritad", "revoltad", "indignad", "vergonha",
            "ladrao", "ladroes", "corrupt", "mentiros", "mentira", "lixo", "merda",
            "pessimo", "pessima", "horrivel", "absurdo", "palhacada", "nojo", "nojent",
            "roubo", "roubar", "golpe", "idiota", "imbecil",
        },
        "sadness": {
            "triste", "tristeza", "decepcao", "decepcion", "chorar", "chorando", "choro",
            "saudade", "luto", "lamentavel", "infelizmente", "sofrer", "sofrendo",
            "morte", "morreu", "tragedia",
        },
        "fear": {
            "medo", "assustad", "preocupad", "ansiedade", "ansios", "panico", "perigo",
            "perigos", "ameaca", "crise", "incerteza", "insegur", "desemprego",
        },
        "neg": {"ruim", "mal", "pior", "fracasso", "problema", "caro", "lento", "erro"},
        "negations": {"nao", "nem", "nunca", "jamais", "sem", "nada", "ninguem"},
        "intensifiers": {"muito", "demais", "super", "bem", "totalmente", "tao", "mega"},
    },
    "fr": {
        "joy": {
            "heureux", "heureuse", "content", "contente", "genial", "super", "excellent",
            "magnifique", "bravo", "merci", "adore", "parfait", "formidable", "bonheur",
            "joie", "fier", "fiere", "felicit", "reussite", "victoire", "top", "mdr",
        },
        "anger": {
            "colere", "furieux", "furieuse", "enerve", "marre", "honte", "scandale",
            "scandaleux", "nul", "nulle", "arnaque", "voleur", "voleurs", "menteur",
            "mensonge", "degoute", "putain", "merde", "connard", "inadmissible",
            "revoltant", "haine", "deteste",
        },
        "sadness": {
            "triste", "tristesse", "deprime", "decu", "decue", "decevant", "pleure",
            "pleurer", "chagrin", "dommage", "helas", "deuil", "malheureusement",
            "souffr",
        },
        "fear": {
            "peur", "effraye", "inquiet", "inquiete", "angoisse", "crainte", "danger",
            "dangereu", "menace", "panique", "crise", "incertitude",
        },
        "neg": {"mauvais", "mauvaise", "pire", "echec", "probleme", "cher", "lent"},
        "negations": {"ne", "pas", "jamais", "sans", "aucun", "aucune", "rien", "personne"},
        "intensifiers": {"tres", "trop", "vraiment", "tellement", "completement", "totalement"},
    },
    "de": {
        "joy": {
            "gluck", "glucklich", "froh", "freue", "freude", "toll", "super", "klasse",
            "genial", "wunderbar", "fantastisch", "perfekt", "danke", "stolz", "liebe",
            "erfolg", "sieg", "hurra", "prima",
        },
        "anger": {
            "wutend", "wut", "sauer", "hasse", "hass", "arger", "argerlich", "skandal",
            "betrug", "lugner", "luge", "schande", "unverschamt", "frechheit", "mist",
            "scheisse", "idiot", "idioten", "korrupt", "empor",
        },
        "sadness": {
            "traurig", "trauer", "schade", "enttausch", "weinen", "leider", "verlust",
            "tragisch", "tragodie", "leid", "vermisse",
        },
        "fear": {
            "angst", "sorge", "sorgen", "besorgt", "furcht", "panik", "gefahr",
            "gefahrlich", "bedroh", "krise", "unsicher",
        },
        "neg": {"schlecht", "schlimm", "schlimmer", "problem", "teuer", "katastrophe"},
        "negations": {"nicht", "kein", "keine", "keinen", "nie", "niemals", "ohne", "nichts"},
        "intensifiers": {"sehr", "total", "extrem", "voll", "echt", "wirklich", "richtig"},
    },
    "it": {
        "joy": {
            "felice", "felici", "contento", "contenta", "bellissim", "fantastic",
            "ottimo", "ottima", "grazie", "adoro", "bravo", "brava", "stupend",
            "evviva", "orgoglio", "vittoria", "success", "perfetto", "meraviglios",
        },
        "anger": {
            "rabbia", "arrabbiat", "furioso", "furiosa", "odio", "vergogna", "schifo",
            "ladri", "ladro", "bugiard", "truffa", "incazzat", "basta", "corrott",
            "scandalo", "idiota", "merda",
        },
        "sadness": {
            "triste", "tristezza", "deluso", "delusa", "deludente", "piango", "piangere",
            "dolore", "peccato", "purtroppo", "lutto", "tragedia",
        },
        "fear": {
            "paura", "spaventat", "preoccupat", "ansia", "pericolo", "pericolos",
            "minaccia", "panico", "crisi", "incertezza",
        },
        "neg": {"brutto", "brutta", "peggio", "peggiore", "fallimento", "problema", "caro"},
        "negations": {"non", "mai", "senza", "nessun", "nessuno", "niente", "nulla"},
        "intensifiers": {"molto", "troppo", "davvero", "tanto", "proprio", "super"},
    },
}
