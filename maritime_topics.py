"""
Maritime Topics — 50+ denizcilik konu havuzu
YouTube Shorts için rastgele veya kategoriye göre konu seçimi.
"""

import random

MARITIME_TOPICS = {
    "mega_ships": {
        "label": "🚢 Mega Ships & Cargo",
        "ideas": [
            "How a 400-meter container ship navigates through the Suez Canal",
            "Inside the engine room of the world's largest cargo ship",
            "What happens when a container falls off a ship in the middle of the ocean",
            "The incredible process of loading 20,000 containers onto a single ship",
            "How ships survive 15-meter waves in the North Atlantic",
            "The world's biggest ship vs the world's smallest tugboat",
            "Why container ships are painted red below the waterline",
            "How a 200,000-ton tanker stops — it takes 3 miles",
            "The secret life of a cargo ship captain crossing the Pacific",
            "How ships navigate through dense fog with zero visibility",
        ],
        "style": "Cinematic aerial drone footage, massive scale contrast, dramatic ocean backdrop, blue-teal color grading, slow sweeping camera movements",
    },
    "storms_and_waves": {
        "label": "🌊 Ocean Storms & Waves",
        "ideas": [
            "A fishing boat caught in a monster rogue wave",
            "What a Category 5 hurricane looks like from a ship's bridge",
            "The tallest wave ever recorded — and the ship that survived it",
            "How cruise ships handle 20-foot swells in open ocean",
            "The terrifying moment a cargo ship rolls 45 degrees in a storm",
            "Why some waves appear out of nowhere in calm seas",
            "How offshore oil rigs survive the most violent ocean storms",
            "The physics behind monster waves that sink ships",
            "A time-lapse of a storm building over the open Atlantic",
            "How sailors predicted storms before modern technology existed",
        ],
        "style": "Dramatic cinematic footage, dark moody sky, massive wave spray, low-angle shots, intense stormy atmosphere, desaturated blue-gray palette",
    },
    "lighthouses": {
        "label": "🏗️ Lighthouses & Navigation",
        "ideas": [
            "The loneliest lighthouse in the world — 300 miles from any land",
            "How lighthouse keepers survived months of total isolation",
            "The incredible engineering of a lighthouse built on open ocean rock",
            "Why some lighthouses have different flash patterns",
            "The haunted lighthouse that no keeper would stay at",
            "How modern GPS replaced 2000 years of lighthouse navigation",
            "The most dangerous lighthouse to maintain in the world",
            "Building a lighthouse in the middle of a raging sea",
        ],
        "style": "Atmospheric cinematic footage, dramatic beam of light cutting through fog, golden hour or stormy twilight, isolated rugged coastline, moody lighting",
    },
    "marine_life": {
        "label": "🐋 Marine Life & Ships",
        "ideas": [
            "A blue whale surfacing next to a massive cargo ship",
            "Dolphins racing alongside a navy destroyer at full speed",
            "The barnacles growing on a ship hull — and why they cost millions",
            "How ships avoid hitting whales in busy shipping lanes",
            "Bioluminescent plankton lighting up a ship's wake at night",
            "A great white shark circling a small fishing vessel",
            "The strange deep-sea creatures found on sunken shipwrecks",
            "How coral reefs grow on abandoned ships over decades",
        ],
        "style": "Underwater and surface split-shot cinematography, crystal clear turquoise water, natural light rays penetrating ocean surface, marine blue palette",
    },
    "shipbuilding": {
        "label": "🔨 Shipbuilding & Engineering",
        "ideas": [
            "How a cruise ship is built from scratch — 3 years in 60 seconds",
            "The moment a brand new ship touches water for the first time",
            "How they weld steel plates underwater to repair a damaged hull",
            "The world's largest dry dock — where aircraft carriers are born",
            "How ship propellers are made — each one weighs 100 tons",
            "The incredible precision of cutting steel for a ship's hull",
            "How nuclear submarines are assembled in secret shipyards",
            "Ship launching gone wrong — the most dramatic ship launches ever",
        ],
        "style": "Industrial cinematic footage, sparks and welding glow, massive steel structures, crane silhouettes, warm industrial orange lighting with cool blue shadows",
    },
    "offshore": {
        "label": "⛽ Offshore & Oil Rigs",
        "ideas": [
            "Life on an offshore oil rig — 200 miles from shore",
            "How helicopter pilots land on a moving oil rig in a storm",
            "The deepest offshore drilling platform in the world",
            "How offshore wind turbines are installed in the open ocean",
            "What happens when an oil rig catches fire in the middle of the sea",
            "The supply ships that keep oil rigs alive — running 24/7",
            "How divers work 300 meters below the surface on pipeline repairs",
            "Decommissioning an oil rig — the billion-dollar demolition",
        ],
        "style": "Dramatic industrial cinematography, aerial wide shots of isolated structures in vast ocean, fire and metal contrast, twilight golden hour, epic scale",
    },
    "maritime_history": {
        "label": "🏴‍☠️ Maritime History",
        "ideas": [
            "The Titanic's final moments — what really happened below deck",
            "How Viking longships crossed the Atlantic 500 years before Columbus",
            "The ghost ship Mary Celeste — found sailing with no crew aboard",
            "The Bermuda Triangle — 5 ships that vanished without a trace",
            "How ancient Phoenician sailors navigated using only the stars",
            "The biggest naval battle in history — with 200,000 sailors",
            "The pirate ship that terrorized the Caribbean for a decade",
            "How they discovered the Titanic wreck 4 km below the surface",
        ],
        "style": "Cinematic historical recreation style, aged film grain, dramatic lighting through fog, atmospheric mist, sepia and deep blue color grading",
    },
    "icebreakers_polar": {
        "label": "🧊 Icebreakers & Polar Seas",
        "ideas": [
            "How nuclear icebreakers smash through 3-meter Arctic ice",
            "The Northern Sea Route — shipping's most dangerous shortcut",
            "What happens when a ship gets stuck in polar ice for months",
            "The incredible power of a Russian nuclear icebreaker's engines",
            "How icebergs are tracked to prevent another Titanic disaster",
            "Life aboard an Antarctic research vessel in -50°C temperatures",
            "The race to cross the Northwest Passage before winter closes in",
        ],
        "style": "Stark polar cinematography, brilliant white ice contrasting dark hull, aerial views of ice-breaking paths, cold blue-white palette, breath vapor visible",
    },
    "fishing": {
        "label": "🎣 Commercial Fishing",
        "ideas": [
            "Hauling in a 500kg bluefin tuna on a longline vessel",
            "The most dangerous fishing job — crab fishing in the Bering Sea",
            "How deep-sea trawlers operate in total darkness at 1000 meters",
            "A day in the life of a swordfish spearfisherman",
            "How factory ships process 200 tons of fish per day at sea",
            "The ancient Japanese art of fishing with trained cormorants",
            "Night fishing with powerful lights that attract squid from the deep",
        ],
        "style": "Raw documentary cinematography, spray and salt water on lens, golden dawn light, working hands pulling nets, authentic gritty ocean atmosphere",
    },
    "ports_and_operations": {
        "label": "🏗️ Ports & Maritime Operations",
        "ideas": [
            "How the world's busiest port moves 40 million containers per year",
            "The incredible precision of a tugboat docking a massive cruise ship",
            "How canal locks lift ships 26 meters — the Panama Canal explained",
            "The robot cranes that load ships with zero human operators",
            "What happens inside a ship's bridge during port approach",
            "How pilots board moving ships using a rope ladder in rough seas",
            "The underground tunnels sailors never see — how harbors really work",
        ],
        "style": "Timelapse and cinematic crane shots, geometric container patterns, massive scale human-machine interaction, night port lighting with sodium lamp glow",
    },
    "submarines": {
        "label": "🔱 Submarines & Underwater",
        "ideas": [
            "How submarines dive to 400 meters and survive crushing pressure",
            "Life inside a nuclear submarine for 90 days without surfacing",
            "The deepest submarine dive ever — 11,000 meters into the Mariana Trench",
            "How submarines navigate in total darkness using only sonar",
            "The emergency procedures when a submarine loses power underwater",
            "How torpedo tubes work inside a military submarine",
            "The secret communication system submarines use underwater",
        ],
        "style": "Dark atmospheric underwater cinematography, sonar green glow, claustrophobic interior shots, deep ocean blue-black, mysterious ambient lighting",
    },
    "ocean_scenery": {
        "label": "🌅 Ocean Scenery & Nature",
        "ideas": [
            "A breathtaking sunset from the deck of a sailboat in the Pacific",
            "The Northern Lights reflected on a perfectly calm Arctic sea",
            "A ship sailing through a field of glowing bioluminescent waters",
            "Dawn breaking over the open ocean — when sky meets sea",
            "A massive waterspout forming next to a sailing yacht",
            "The crystal-clear turquoise waters of the Maldives from above",
            "A thunderstorm approaching over a mirror-flat tropical ocean",
        ],
        "style": "Stunning nature cinematography, vibrant saturated colors, golden hour lighting, mirror-calm water reflections, 4K clarity wide panoramic shots",
    },
}


def get_random_topic() -> dict:
    """Rastgele bir konu kategorisinden rastgele bir fikir seç."""
    category_key = random.choice(list(MARITIME_TOPICS.keys()))
    category = MARITIME_TOPICS[category_key]
    idea = random.choice(category["ideas"])
    return {
        "category": category_key,
        "label": category["label"],
        "idea": idea,
        "style": category["style"],
    }


def get_topic_from_category(category_key: str) -> dict:
    """Belirli bir kategoriden rastgele bir fikir seç."""
    if category_key not in MARITIME_TOPICS:
        raise ValueError(f"Unknown category: {category_key}. Available: {list(MARITIME_TOPICS.keys())}")
    category = MARITIME_TOPICS[category_key]
    idea = random.choice(category["ideas"])
    return {
        "category": category_key,
        "label": category["label"],
        "idea": idea,
        "style": category["style"],
    }


def get_all_categories() -> list[dict]:
    """Tüm kategorileri listele."""
    return [
        {"key": k, "label": v["label"], "count": len(v["ideas"])}
        for k, v in MARITIME_TOPICS.items()
    ]


def get_total_topic_count() -> int:
    """Toplam konu sayısını döndür."""
    return sum(len(v["ideas"]) for v in MARITIME_TOPICS.values())
