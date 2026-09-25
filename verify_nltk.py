import nltk
from nltk.stem import WordNetLemmatizer
import os

try:
    print(f"Testing NLTK version: {nltk.__version__}")
    
    # Ensure resources are downloaded (mirroring logic in views.py)
    try:
        nltk.data.find('corpora/wordnet.zip')
    except LookupError:
        print("Downloading wordnet...")
        nltk.download('wordnet')
        
    try:
        nltk.data.find('corpora/omw-1.4.zip')
    except LookupError:
        print("Downloading omw-1.4...")
        nltk.download('omw-1.4')

    lemmatizer = WordNetLemmatizer()
    result = lemmatizer.lemmatize("running", pos="v")
    print(f"Lemmatizing 'running' -> {result}")
    
    if result == 'run':
        print("SUCCESS")
    else:
        print("FAILURE: Unexpected lemmatization result")
        
except Exception as e:
    print(f"FAILURE: {e}")
