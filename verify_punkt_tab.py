import nltk

try:
    print("Checking for punkt_tab...")
    nltk.data.find('tokenizers/punkt_tab')
    print("punkt_tab found!")
    
    print("Testing sentence tokenization...")
    text = "Hello world. This is a test."
    sentences = nltk.sent_tokenize(text)
    print(f"Tokenized sentences: {sentences}")
    
    if len(sentences) == 2:
        print("SUCCESS: specific punkt_tab functionality (via sent_tokenize) working.")
    else:
        print("FAILURE: Unexpected tokenization result.")

except LookupError:
    print("FAILURE: punkt_tab not found.")
except Exception as e:
    print(f"FAILURE: {e}")
