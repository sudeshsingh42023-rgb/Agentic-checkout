"""
Generates a ~500-SKU catalog into catalog.json — deliberately varied
descriptions (not just "Blue Jacket M") so semantic search actually has
to do work beyond keyword matching.
"""
import json
import random

random.seed(7)

CATEGORIES = {
    "Running Jackets": [
        "{color} waterproof running jacket with reflective piping, packs into its own pocket",
        "{color} lightweight windbreaker for trail running, breathable mesh lining",
        "{color} thermal running jacket for cold-weather training, fleece-lined collar",
    ],
    "Sneakers": [
        "{color} cushioned daily-trainer sneaker, good for long-distance running",
        "{color} minimalist sneaker for casual everyday wear, canvas upper",
        "{color} high-top basketball sneaker with ankle support",
    ],
    "Backpacks": [
        "{color} 25L hiking backpack with hydration bladder compartment",
        "{color} slim laptop backpack for commuting, fits up to 15-inch laptops",
        "{color} rolltop waterproof backpack for cycling commuters",
    ],
    "Yoga Wear": [
        "{color} high-waisted yoga leggings, four-way stretch fabric",
        "{color} breathable yoga tank top, moisture-wicking",
        "{color} yoga wrap top with adjustable tie-back",
    ],
    "Winter Wear": [
        "{color} insulated puffer jacket rated for sub-zero temperatures",
        "{color} merino wool beanie, machine washable",
        "{color} fleece-lined winter gloves with touchscreen fingertips",
    ],
}
COLORS = ["Black", "Navy", "Charcoal", "Olive", "Maroon", "Slate Grey", "Forest Green", "White"]
SIZES = ["XS", "S", "M", "L", "XL", "XXL"]


def generate_catalog(n=500):
    catalog = []
    pid = 1
    cats = list(CATEGORIES.items())
    while len(catalog) < n:
        cat, templates = random.choice(cats)
        template = random.choice(templates)
        color = random.choice(COLORS)
        size = random.choice(SIZES)
        price = round(random.uniform(499, 6999), 2)
        desc = template.format(color=color)
        catalog.append({
            "id": pid,
            "name": f"{color} {cat[:-1] if cat.endswith('s') else cat}",
            "category": cat,
            "description": desc,
            "size": size,
            "color": color,
            "price": price,
            "stock": random.randint(0, 60),
        })
        pid += 1

    with open("catalog.json", "w") as f:
        json.dump(catalog, f, indent=2)
    print(f"Generated {len(catalog)} products -> catalog.json")


if __name__ == "__main__":
    generate_catalog(500)
