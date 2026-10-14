"""Curated collection spec for a fresh Nuvio account.

Every source is a Nuvio-native TMDB or Trakt source, so the whole setup works with no
catalog addons installed. Field names follow CollectionModels.kt in Nuvio 0.1.30.
"""

NOISE_TV = "10763|10767|10766"  # News, Talk, Soap: keep daily/filler shows out of series rails

# Vote-count floors. "global" for big catalogues, "regional" for smaller ones.
FLOORS = {
    "global": dict(pop_m=100, pop_t=50, top_m=1000, top_t=300, new_m=25, new_t=15),
    "mid": dict(pop_m=30, pop_t=20, top_m=200, top_t=80, new_m=10, new_t=5),
    "regional": dict(pop_m=10, pop_t=5, top_m=60, top_t=25, new_m=4, new_t=3),
    "india": dict(pop_m=8, pop_t=3, top_m=40, top_t=10, new_m=3, new_t=1),
    "india_small": dict(pop_m=3, pop_t=1, top_m=15, top_t=4, new_m=1, new_t=1),
}


def _clean(d):
    return {k: v for k, v in d.items() if v not in (None, "")}


def discover(title, media, sort=None, **filters):
    if media == "tv" and "withoutGenres" not in filters:
        filters["withoutGenres"] = NOISE_TV
    return _clean({
        "provider": "tmdb",
        "tmdbSourceType": "DISCOVER",
        "title": title,
        "mediaType": media,
        "sortBy": sort,
        "filters": _clean(filters),
    })


def network(title, net_id, sort=None, **filters):
    filters.setdefault("withoutGenres", NOISE_TV)
    return _clean({
        "provider": "tmdb",
        "tmdbSourceType": "NETWORK",
        "title": title,
        "tmdbId": net_id,
        "mediaType": "tv",
        "sortBy": sort,
        "filters": _clean(filters),
    })


def company(title, company_id, media="movie", sort=None, **filters):
    if media == "tv":
        filters.setdefault("withoutGenres", NOISE_TV)
    return _clean({
        "provider": "tmdb",
        "tmdbSourceType": "COMPANY",
        "title": title,
        "tmdbId": company_id,
        "mediaType": media,
        "sortBy": sort,
        "filters": _clean(filters),
    })


def collection(title, coll_id, sort=None):
    return _clean({"provider": "tmdb", "tmdbSourceType": "COLLECTION", "title": title,
                   "tmdbId": coll_id, "mediaType": "movie", "sortBy": sort})


def director(title, person_id, media="movie", sort=None):
    return _clean({"provider": "tmdb", "tmdbSourceType": "DIRECTOR", "title": title,
                   "tmdbId": person_id, "mediaType": media, "sortBy": sort})


# ---- tab presets -----------------------------------------------------------------

def standard_tabs(floor="global", movies=True, series=True, label_m="Movies", label_t="Series",
                  new=True, top=True, **f):
    """Popular / New / Top Rated rails for a filter set (provider, genre, language...)."""
    fl = FLOORS[floor]
    fm = {k: v for k, v in f.items() if not k.startswith("tv_")}
    ft = {k: v for k, v in f.items() if not k.startswith("m_")}
    fm = {k.removeprefix("m_"): v for k, v in fm.items()}
    ft = {k.removeprefix("tv_"): v for k, v in ft.items()}
    out = []
    if movies:
        out.append(discover(f"Popular {label_m}", "movie", None, voteCountGte=fl["pop_m"], **fm))
    if series:
        out.append(discover(f"Popular {label_t}", "tv", None, voteCountGte=fl["pop_t"], **ft))
    if new and movies:
        out.append(discover(f"New {label_m}", "movie", "primary_release_date.desc", voteCountGte=fl["new_m"], **fm))
    if new and series:
        out.append(discover(f"New {label_t}", "tv", "first_air_date.desc", voteCountGte=fl["new_t"], **ft))
    if top and movies:
        out.append(discover(f"Top Rated {label_m}", "movie", "vote_average.desc", voteCountGte=fl["top_m"], **fm))
    if top and series:
        out.append(discover(f"Top Rated {label_t}", "tv", "vote_average.desc", voteCountGte=fl["top_t"], **ft))
    return out


def service_tabs(providers, region, floor="global", originals=None, originals_label=None,
                 movies=True, series=True, origin=None):
    base = dict(withWatchProviders=providers, watchRegion=region)
    if origin:
        base["withOriginCountry"] = origin
    tabs = []
    if originals:
        nets = originals if isinstance(originals, list) else [originals]
        tabs.append(_clean({
            "provider": "tmdb", "tmdbSourceType": "NETWORK", "title": originals_label or "Originals",
            "tmdbId": nets[0], "mediaType": "tv",
            "filters": _clean({"withoutGenres": NOISE_TV, "releaseDateGte": "2012-01-01",
                               "withNetworks": "|".join(map(str, nets[1:])) or None,
                               "withOriginCountry": origin}),
        }))
    tabs += standard_tabs(floor, movies=movies, series=series, **base)
    return tabs


# ---- the curation ----------------------------------------------------------------
# Each folder: (title, sources, art) where art tells the cover renderer what to draw.

SERVICES = [
    # title, providers, region, originals network(s), logo key
    ("Netflix", "8|1796", "US", [213], "netflix"),
    ("Prime Video", "9|2100", "US", [1024], "prime-video"),
    ("Disney+", "337", "US", [2739], "disney-plus"),
    ("HBO Max", "1899", "US", [49, 3186], "hbo-max"),
    ("Apple TV", "350", "US", [2552], "apple-tv"),
    ("Hulu", "15", "US", [453], "hulu"),
    ("Paramount+", "2303|2616", "US", [4330], "paramount-plus"),
    ("Peacock", "386|387", "US", [3353], "peacock"),
    ("Crunchyroll", "283", "US", [1112], "crunchyroll"),
    ("Starz", "43", "US", [318], "starz"),
    ("MGM+", "34", "US", [6219, 922], "mgm-plus"),
    ("AMC+", "526", "US", [174], "amc-plus"),
    ("Shudder", "99", "US", [2949], "shudder"),
    ("MUBI", "11", "US", None, "mubi"),
    ("Criterion Channel", "258", "US", None, "criterion"),
]

INDIA_SERVICES = [
    ("JioHotstar", "2336", [3919, 8036], "jiohotstar", "mid"),
    ("Netflix India", "8", [213], "netflix", "mid"),
    ("Prime Video India", "119", [1024], "prime-video", "mid"),
    ("SonyLIV", "237", [2646], "sonyliv", "india"),
    ("ZEE5", "232", [2590], "zee5", "india"),
    ("Amazon MX Player", "1898|515", [2964], "mx-player", "india"),
    ("aha", "532", [3758], "aha", "india_small"),
    ("Sun NXT", "309", None, "sun-nxt", "india_small"),
    ("Hoichoi", "315", [2139], "hoichoi", "india_small"),
    ("ManoramaMAX", "482", [9538], "manorama-max", "india_small"),
    ("Lionsgate Play", "561", None, "lionsgate-play", "india_small"),
    ("ShemarooMe", "474", None, "shemaroo-me", "india_small"),
]

# (title, movie genres, tv genres, extra kw)
GENRES = [
    ("Action", "28", "10759"),
    ("Adventure", "12", "10759"),
    ("Comedy", "35", "35"),
    ("Drama", "18", "18"),
    ("Thriller", "53", "80|9648"),
    ("Crime", "80", "80"),
    ("Horror", "27", None),
    ("Sci-Fi", "878", "10765"),
    ("Fantasy", "14", "10765"),
    ("Romance", "10749", None),
    ("Mystery", "9648", "9648"),
    ("Animation", "16", "16"),
    ("Family", "10751", "10751"),
    ("Kids", "10751|16", "10762"),
    ("Documentary", "99", "99"),
    ("History", "36", "10768"),
    ("War", "10752", "10768"),
    ("Western", "37", "37"),
    ("Music", "10402", None),
    ("Reality", None, "10764"),
]

INDIAN_CINEMA = [
    # title, language, label for the movies rail
    ("Bollywood", "hi"),
    ("Telugu", "te"),
    ("Tamil", "ta"),
    ("Malayalam", "ml"),
    ("Kannada", "kn"),
    ("Bengali", "bn"),
    ("Marathi", "mr"),
    ("Punjabi", "pa"),
]

WORLD = [
    # title, filters for movies, filters for tv, floor
    ("Korean", dict(withOriginalLanguage="ko"), dict(withOriginalLanguage="ko"), "global", "K-Dramas"),
    ("Anime", dict(withOriginalLanguage="ja", withGenres="16"), dict(withOriginalLanguage="ja", withGenres="16"), "global", "Anime Series"),
    ("Japanese", dict(withOriginalLanguage="ja", withoutGenres="16"), dict(withOriginalLanguage="ja", withoutGenres="16|" + NOISE_TV), "mid", "J-Dramas"),
    ("Chinese", dict(withOriginalLanguage="zh|cn"), dict(withOriginalLanguage="zh"), "mid", "C-Dramas"),
    ("Turkish", dict(withOriginalLanguage="tr"), dict(withOriginalLanguage="tr"), "mid", "Dizi"),
    ("Spanish", dict(withOriginalLanguage="es", withOriginCountry="ES"), dict(withOriginalLanguage="es", withOriginCountry="ES"), "mid", "Series"),
    ("Latin American", dict(withOriginCountry="MX|AR|CO|CL|BR|PE"), dict(withOriginCountry="MX|AR|CO|CL|BR|PE"), "mid", "Series"),
    ("French", dict(withOriginalLanguage="fr"), dict(withOriginalLanguage="fr"), "mid", "Series"),
    ("Italian", dict(withOriginalLanguage="it"), dict(withOriginalLanguage="it"), "mid", "Series"),
    ("German", dict(withOriginalLanguage="de"), dict(withOriginalLanguage="de"), "mid", "Series"),
    ("Nordic", dict(withOriginalLanguage="sv|da|no|fi|is"), dict(withOriginalLanguage="sv|da|no|fi|is"), "mid", "Nordic Noir"),
    ("British", dict(withOriginCountry="GB", withOriginalLanguage="en"), dict(withOriginCountry="GB", withOriginalLanguage="en"), "global", "Series"),
    ("Thai", dict(withOriginalLanguage="th"), dict(withOriginalLanguage="th"), "regional", "Series"),
    ("Filipino", dict(withOriginalLanguage="tl"), dict(withOriginalLanguage="tl"), "regional", "Series"),
    ("Arabic", dict(withOriginalLanguage="ar"), dict(withOriginalLanguage="ar"), "regional", "Series"),
    ("African", dict(withOriginCountry="NG|KE|ZA|GH|SN|ET|TZ|UG|CM|CI"), dict(withOriginCountry="NG|KE|ZA|GH|SN|ET|TZ|UG|CM|CI"), "regional", "Series"),
]

STUDIOS = [
    # title, company id(s) (first = tmdbId, rest via withCompanies), media, logo key
    ("Marvel Studios", [420], "movie"),
    ("Lucasfilm", [1], "movie"),
    ("Pixar", [3], "movie"),
    ("Walt Disney Animation", [6125], "movie"),
    ("Walt Disney Pictures", [2], "movie"),
    ("DreamWorks Animation", [521], "movie"),
    ("Illumination", [6704], "movie"),
    ("Studio Ghibli", [10342], "movie"),
    ("DC", [9993, 184898, 128064], "movie"),
    ("Warner Bros.", [174], "movie"),
    ("Universal", [33], "movie"),
    ("Paramount", [4], "movie"),
    ("20th Century", [127928, 25], "movie"),
    ("Sony Pictures", [5, 2251], "movie"),
    ("Legendary", [923], "movie"),
    ("A24", [41077], "movie"),
    ("NEON", [90733], "movie"),
    ("Blumhouse", [3172], "movie"),
    ("Searchlight", [127929, 43], "movie"),
    ("Amblin", [56], "movie"),
    ("Lionsgate", [1632], "movie"),
    ("LAIKA", [11537], "movie"),
    ("Aardman", [297], "movie"),
    ("Yash Raj Films", [1569], "movie"),
    ("Dharma Productions", [19146], "movie"),
    ("Red Chillies", [2343], "movie"),
    ("Hombale Films", [111627], "movie"),
    ("Mythri Movie Makers", [69125], "movie"),
    ("Toho", [882], "movie"),
    ("MAPPA", [21444], "tv"),
    ("ufotable", [5887], "tv"),
]

NETWORKS = [
    ("HBO", [49]),
    ("FX", [88]),
    ("AMC", [174]),
    ("Showtime", [67]),
    ("BBC", [4, 332, 3]),
    ("Channel 4", [26]),
    ("ITV", [9]),
    ("NBC", [6]),
    ("ABC", [2]),
    ("CBS", [16]),
    ("FOX", [19]),
    ("The CW", [71]),
    ("Adult Swim", [80]),
    ("Cartoon Network", [56]),
    ("Nickelodeon", [13]),
    ("Disney Channel", [54]),
    ("National Geographic", [43]),
    ("Discovery", [64]),
    ("History", [65]),
    ("Comedy Central", [47]),
    ("tvN", [866]),
    ("JTBC", [885]),
]

# Franchises: title, list of (tab title, source) built below; art = (backdrop collection or movie, logo movie id)
FRANCHISES = [
    ("Marvel Cinematic Universe", [
        discover("Films", "movie", "primary_release_date.asc", withKeywords="180547", voteCountGte=200),
        discover("Series", "tv", "first_air_date.asc", withKeywords="180547", voteCountGte=20)]),
    ("Star Wars", [collection("Skywalker Saga", 10),
                   discover("All Films", "movie", "primary_release_date.asc", withCompanies="1", withKeywords="161176", voteCountGte=400),
                   discover("Series", "tv", "first_air_date.asc", withCompanies="1", withGenres="10765", voteCountGte=80)]),
    ("Wizarding World", [collection("Harry Potter", 1241), collection("Fantastic Beasts", 435259)]),
    ("Middle-earth", [collection("The Lord of the Rings", 119), collection("The Hobbit", 121938)]),
    ("DC Universe", [
        discover("Films", "movie", "primary_release_date.desc", withKeywords="229266|312528", voteCountGte=200),
        collection("The Dark Knight Trilogy", 263),
        discover("Series", "tv", None, withKeywords="312528|229266", voteCountGte=20)]),
    ("James Bond", [collection("007", 645)]),
    ("Mission: Impossible", [collection("Mission: Impossible", 87359)]),
    ("Fast & Furious", [collection("Fast & Furious", 9485)]),
    ("John Wick", [collection("John Wick", 404609)]),
    ("Jurassic Park", [collection("Jurassic Park & World", 328)]),
    ("Spider-Man", [collection("Spider-Man", 556), collection("MCU", 531241), collection("Spider-Verse", 573436)]),
    ("X-Men", [collection("X-Men", 748), collection("Deadpool", 448150), collection("Wolverine", 453993)]),
    ("MonsterVerse", [discover("Films", "movie", "primary_release_date.asc", withKeywords="380322"),
                       discover("Series", "tv", "first_air_date.asc", withKeywords="380322")]),
    ("Dune", [collection("Dune", 726871)]),
    ("Avatar", [collection("Avatar", 87096)]),
    ("The Matrix", [collection("The Matrix", 2344)]),
    ("Alien & Predator", [collection("Alien", 8091), collection("Predator", 399)]),
    ("Pirates of the Caribbean", [collection("Pirates", 295)]),
    ("The Hunger Games", [collection("The Hunger Games", 131635)]),
    ("Indiana Jones", [collection("Indiana Jones", 84)]),
    ("The Godfather", [collection("The Godfather", 230)]),
    ("Back to the Future", [collection("Back to the Future", 264)]),
    ("Planet of the Apes", [collection("Reboot", 173710), collection("Original", 1709)]),
    ("Rocky & Creed", [collection("Rocky", 1575), collection("Creed", 553717)]),
    ("Mad Max", [collection("Mad Max", 8945)]),
    ("The Terminator", [collection("The Terminator", 528)]),
    ("Bourne", [collection("Bourne", 31562)]),
    ("Toy Story", [collection("Toy Story", 10194)]),
    ("Shrek", [collection("Shrek", 2150)]),
    ("Despicable Me", [collection("Despicable Me", 86066), collection("Minions", 544669)]),
    ("How to Train Your Dragon", [collection("Animated", 89137), collection("Live-Action", 1458864)]),
    ("Kung Fu Panda", [collection("Kung Fu Panda", 77816)]),
    ("The Conjuring Universe", [collection("The Conjuring", 313086), collection("Annabelle", 402074), collection("The Nun", 968052)]),
]

INDIAN_FRANCHISES = [
    ("Baahubali", [collection("Baahubali", 350309)]),
    ("K.G.F", [collection("K.G.F", 657153)]),
    ("Pushpa", [collection("Pushpa", 921781)]),
    ("YRF Spy Universe", [collection("Tiger", 485645), discover("Spy Universe", "movie", "primary_release_date.asc", withCompanies="1569", withKeywords="470", voteCountGte=40)]),
    ("Cop Universe", [discover("Films", "movie", "primary_release_date.asc", withKeywords="287118")]),
    ("Lokesh Cinematic Universe", [discover("Films", "movie", "primary_release_date.asc", withKeywords="352123")]),
    ("Horror Comedy Universe", [discover("Films", "movie", "primary_release_date.asc", withKeywords="359782")]),
    ("Dhoom", [collection("Dhoom", 44976)]),
    ("Krrish", [collection("Krrish", 246091)]),
    ("Golmaal", [collection("Golmaal", 483464)]),
    ("Hera Pheri", [collection("Hera Pheri", 142022)]),
    ("Drishyam", [collection("Malayalam", 787649), collection("Hindi", 1029834)]),
]

DIRECTORS = [
    ("Christopher Nolan", 525), ("Denis Villeneuve", 137427), ("Quentin Tarantino", 138),
    ("Martin Scorsese", 1032), ("Steven Spielberg", 488), ("David Fincher", 7467),
    ("Stanley Kubrick", 240), ("Ridley Scott", 578), ("James Cameron", 2710),
    ("Bong Joon Ho", 21684), ("Park Chan-wook", 10099), ("Hayao Miyazaki", 608),
    ("Guillermo del Toro", 10828), ("Wes Anderson", 5655), ("Greta Gerwig", 45400),
    ("Paul Thomas Anderson", 4762), ("Jordan Peele", 291263), ("Alfred Hitchcock", 2636),
    ("Akira Kurosawa", 5026), ("Wong Kar-wai", 12453), ("S. S. Rajamouli", 147021),
    ("Mani Ratnam", 78747), ("Sanjay Leela Bhansali", 42804), ("Rajkumar Hirani", 85675),
    ("Anurag Kashyap", 85670), ("Zoya Akhtar", 80386), ("Lokesh Kanagaraj", 1592411),
    ("Satyajit Ray", 12160),
]

# Moods & themes: title, keywords, optional genre constraint
THEMES = [
    ("Mind-Benders", "362567|326438|10854|157171", None),
    ("Heists", "10051|15363|191845", None),
    ("True Stories", "9672", None),
    ("Superheroes", "9715", None),
    ("Space", "9882|161176|3801", None),
    ("Time Travel", "4379", None),
    ("Dystopia", "4565|4458", None),
    ("Spies", "470", None),
    ("Cyberpunk & AI", "12190|310", None),
    ("Serial Killers", "10714", None),
    ("Whodunits", "12570|207046|703", None),
    ("Survival", "10349", None),
    ("Revenge", "9748", None),
    ("Mafia & Gangsters", "10391|3149", None),
    ("Courtroom", "33519|222517|214780", None),
    ("Political Thrillers", "209817|10410", None),
    ("Martial Arts", "779|780|184656", None),
    ("Zombies", "12377", None),
    ("Monsters & Kaiju", "161791|1299|11100", None),
    ("Vampires", "3133", None),
    ("Disaster", "10617|5096", None),
    ("Coming of Age", "10683", None),
    ("Sports", "6075|209476|13042|6496", None),
    ("Road Trips", "7312", None),
    ("Musicals", "4344", None),
    ("Feel-Good", "383896|275276", None),
    ("Christmas", "207317", None),
    ("Dark Comedy", "10123", None),
    ("Satire", "8201", None),
    ("Neo-Noir", "207268|9807", None),
    ("Video Game Adaptations", "41645", None),
    ("Stand-Up Comedy", "9716", None),
    ("Nature & Wildlife", "221355|9902", None),
    ("Isekai", "237451", None),
]

DECADES = ["2020s", "2010s", "2000s", "1990s", "1980s", "1970s", "1960s", "1950s"]
