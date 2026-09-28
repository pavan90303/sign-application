"""
Centralized Sign Language Vocabulary Registry
============================================
Defines controlled sign vocabularies, token mappings, and semantic categories.
Single source of truth used across Learning, Quiz, Sign-to-English, and Concept Assessment.
"""

CONTROLLED_VOCABULARY = [
    # Academic & Science Concepts
    "PLANT",
    "SUNLIGHT",
    "WATER",
    "CARBON_DIOXIDE",
    "FOOD",
    "OXYGEN",
    "PROCESS",
    "ABSORB",
    "PRODUCE",
    "ENERGY",
    # Core Everyday & Course Foundations
    "HELLO",
    "THANK_YOU",
    "PLEASE",
    "YES",
    "NO",
    "HELP",
    "GOOD",
    "BAD",
    "DAY",
    "NIGHT",
    "HOME",
    "COLLEGE",
    "STUDENT",
    "DOCTOR",
    "HOSPITAL"
]

VOCAB_TO_IDX = {sign: idx for idx, sign in enumerate(CONTROLLED_VOCABULARY)}
IDX_TO_VOCAB = {idx: sign for idx, sign in enumerate(CONTROLLED_VOCABULARY)}

TOKEN_TO_SEMANTIC_CONCEPT = {
    "PLANT": "Plant / Autotroph",
    "SUNLIGHT": "Sunlight / Light Energy",
    "WATER": "Water (H2O)",
    "CARBON_DIOXIDE": "Carbon Dioxide (CO2)",
    "FOOD": "Glucose / Chemical Energy",
    "OXYGEN": "Oxygen Gas (O2)",
    "PROCESS": "Biological Process / Reaction",
    "ABSORB": "Absorption Mechanism",
    "PRODUCE": "Synthesis / Production",
    "ENERGY": "Energy Transformation",
    "HELLO": "Greeting",
    "THANK_YOU": "Appreciation",
    "PLEASE": "Courtesy Request",
    "YES": "Affirmation",
    "NO": "Negation",
    "HELP": "Assistance",
    "GOOD": "Positive Quality",
    "BAD": "Negative Quality",
    "DAY": "Temporal Day",
    "NIGHT": "Temporal Night",
    "HOME": "Domestic Setting",
    "COLLEGE": "Educational Institution",
    "STUDENT": "Learner",
    "DOCTOR": "Medical Professional",
    "HOSPITAL": "Healthcare Facility"
}

# ISL Alphabet tokens
ALPHABET_TOKENS = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")

# Common English and ISL word vocabulary for auto-complete and suggestions
WORD_SUGGESTION_VOCABULARY = [
    "WATER", "FOOD", "EAT", "HELLO", "HELP", "YES", "NO", "PLEASE", "SORRY", "THANK", "THANK_YOU",
    "GOOD", "BAD", "MORNING", "NIGHT", "HOME", "SCHOOL", "FRIEND", "MOTHER", "FATHER", "SISTER",
    "BROTHER", "STUDENT", "TEACHER", "COLLEGE", "COMPUTER", "STUDY", "LEARN", "LANGUAGE",
    "SUNLIGHT", "PLANT", "ENERGY", "SAFE", "TIME", "DAY", "NAME", "WORK", "WELCOME", "BYE",
    "DOCTOR", "HOSPITAL", "PAVAN", "INDIA", "HAPPY", "BEAUTIFUL", "GREAT", "DISTANCE", "WALK",
    "ABOUT", "AFTER", "AGAIN", "ALL", "AND", "ARE", "ASK", "BE", "BECAUSE", "BEFORE",
    "BEST", "BETTER", "BUT", "CAN", "CHANGE", "COME", "DO", "DOES", "EVERY", "FIND",
    "FIRST", "FOR", "FROM", "GIVE", "GO", "HAVE", "HE", "HER", "HERE", "HIM",
    "HIS", "HOW", "IN", "INTO", "IS", "IT", "JUST", "KNOW", "LIKE", "LOOK",
    "MAKE", "ME", "MORE", "MOST", "MY", "NEW", "NOW", "OF", "ON", "ONE",
    "ONLY", "OR", "OTHER", "OUR", "OUT", "OVER", "PEOPLE", "SAY", "SEE", "SHE",
    "SO", "SOME", "TAKE", "TELL", "THAN", "THAT", "THE", "THEIR", "THEM", "THEN",
    "THERE", "THESE", "THEY", "THING", "THINK", "THIS", "TIME", "TO", "TWO", "UP",
    "US", "USE", "VERY", "WANT", "WAY", "WE", "WELL", "WHAT", "WHEN", "WHICH",
    "WHO", "WILL", "WITH", "WORDS", "WORLD", "WOULD", "WRITE", "YEAR", "YOU", "YOUR"
]
