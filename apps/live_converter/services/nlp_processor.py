"""
Live Converter NLP Processor
============================
Tokenizes input English sentences, tags POS, computes probable tense,
lemmatizes words, filters stopwords, and constructs the ISL animation sequence.
"""

import nltk
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
from django.contrib.staticfiles import finders

STOP_WORDS = set([
    "mightn't", 're', 'wasn', 'wouldn', 'be', 'has', 'that', 'does', 'shouldn', 'do', "you've",
    'off', 'for', "didn't", 'm', 'ain', 'haven', "weren't", 'are', "she's", "wasn't", 'its',
    "haven't", "wouldn't", 'don', 'weren', 's', "you'd", "don't", 'doesn', "hadn't", 'is',
    'was', "that'll", "should've", 'a', 'then', 'the', 'mustn', 'i', 'nor', 'as', "it's",
    "needn't", 'd', 'am', 'have', 'hasn', 'o', "aren't", "you'll", "couldn't", "you're",
    "mustn't", 'didn', "doesn't", 'll', 'an', 'hadn', 'whom', 'y', "hasn't", 'itself',
    'couldn', 'needn', "shan't", 'isn', 'been', 'such', 'shan', "shouldn't", 'aren',
    'being', 'were', 'did', 'ma', 't', 'having', 'mightn', 've', "isn't", "won't"
])


def process_text_to_sign_words(text: str) -> list:
    """
    Parses natural English text and resolves it into a sequence of sign video tokens or fingerspelled letters.
    """
    if not text:
        return []

    text_lower = text.lower()

    try:
        words = word_tokenize(text_lower)
    except LookupError:
        nltk.download('punkt', quiet=True)
        nltk.download('punkt_tab', quiet=True)
        words = word_tokenize(text_lower)

    try:
        tagged = nltk.pos_tag(words)
    except LookupError:
        nltk.download('averaged_perceptron_tagger', quiet=True)
        nltk.download('averaged_perceptron_tagger_eng', quiet=True)
        tagged = nltk.pos_tag(words)

    tense = {
        "future": len([word for word in tagged if word[1] == "MD"]),
        "present": len([word for word in tagged if word[1] in ["VBP", "VBZ", "VBG"]]),
        "past": len([word for word in tagged if word[1] in ["VBD", "VBN"]]),
        "present_continuous": len([word for word in tagged if word[1] in ["VBG"]]),
    }

    lr = WordNetLemmatizer()
    try:
        lr.lemmatize('test')
    except (LookupError, AttributeError):
        nltk.download('wordnet', quiet=True)
        nltk.download('omw-1.4', quiet=True)

    filtered_text = []
    for w, p in zip(words, tagged):
        if w not in STOP_WORDS:
            if p[1] in ['VBG', 'VBD', 'VBZ', 'VBN', 'NN']:
                filtered_text.append(lr.lemmatize(w, pos='v'))
            elif p[1] in ['JJ', 'JJR', 'JJS', 'RBR', 'RBS']:
                filtered_text.append(lr.lemmatize(w, pos='a'))
            else:
                filtered_text.append(lr.lemmatize(w))

    words = ['Me' if w == 'I' else w for w in filtered_text]
    probable_tense = max(tense, key=tense.get)

    if probable_tense == "past" and tense["past"] >= 1:
        words = ["Before"] + words
    elif probable_tense == "future" and tense["future"] >= 1:
        if "Will" not in words:
            words = ["Will"] + words
    elif probable_tense == "present" and tense["present_continuous"] >= 1:
        words = ["Now"] + words

    final_sequence = []
    for w in words:
        path = w + ".mp4"
        found = finders.find(path)
        if not found:
            for c in w:
                final_sequence.append(c)
        else:
            final_sequence.append(w)

    return final_sequence
