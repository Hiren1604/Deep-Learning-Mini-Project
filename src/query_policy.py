"""Catalog vocabulary guard for unsupported text searches; no model confidence guesses."""
import re


OUT_OF_SCOPE_MESSAGE = (
    "This catalog covers fashion, accessories and beauty products. "
    "Try a query like ‘women’s shoes’, ‘blue shirt’ or ‘lipstick’."
)


def words(text):
    return set(re.findall(r"[a-z]+", str(text).lower()))


def variants(token):
    forms = {token}
    if token.endswith("ies"):
        forms.add(token[:-3] + "y")
    elif token.endswith(("sses", "ches", "shes", "xes")):
        forms.add(token[:-2])
    elif len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        forms.add(token[:-1])
    return forms


class CatalogQueryPolicy:
    def __init__(self, metadata):
        # Qualifiers such as "sports" or "face" alone are not product names.
        qualifiers = {
            "sports", "casual", "formal", "body", "face", "eye", "lip", "hair",
            "lounge", "night", "rain", "travel", "beauty", "free", "gift", "gifts",
            "set", "sets", "and", "baby", "water", "mobile", "ipad", "tablet",
            "laptop", "mens", "grooming", "wash", "care", "cream", "gel", "milk",
        }
        self.product_words = {
            form for name in metadata.get("articleType", []).dropna()
            for token in words(name) - qualifiers for form in variants(token)
        }
        self.product_words.update({
            "fashion", "clothing", "clothes", "apparel", "outfit", "outfits",
            "footwear", "accessory", "accessories", "makeup", "cosmetic", "cosmetics",
            "skincare", "jewellery", "jewelry", "activewear", "sportswear", "sleepwear",
            "sneaker", "sneakers", "trainer", "trainers", "boot", "boots",
            "tshirt", "tshirts", "tee", "tees", "coat", "coats", "denim",
            "gown", "gowns", "wristwatch", "wristwatches", "tuxedo", "tuxedos",
        })
        self.attributes = {
            form for field in ("gender", "baseColour", "usage", "season")
            if field in metadata for value in metadata[field].dropna()
            for token in words(value) for form in variants(token)
        }
        self.attributes.update({
            "women", "woman", "womens", "female", "ladies", "men", "man", "mens",
            "male", "boys", "boy", "girls", "girl", "kids", "kid", "children",
            "gray", "grey", "comfortable", "breathable", "running", "jogging",
            "wedding", "office", "work", "party", "summer", "winter", "wear",
        })
        # Brand-only searches remain useful; first title words are a conservative
        # proxy because this catalog does not have a separate brand column.
        generic_starts = {"a", "an", "the", "how", "what", "who", "why", "hello"}
        self.brands = {
            str(name).split()[0].lower() for name in metadata["productDisplayName"].dropna()
            if str(name).split()
        } - generic_starts
        self.fillers = {
            "a", "an", "the", "for", "and", "or", "in", "with", "of", "to",
            "me", "my", "i", "want", "need", "find", "show", "search", "buy",
            "looking", "something", "please", "s", "style", "styles",
        }

    def supports(self, query):
        tokens = words(query)
        if not tokens:
            return False
        if tokens & self.product_words:
            return True
        meaningful = tokens - self.fillers
        return bool(meaningful) and meaningful <= (self.attributes | self.brands)
