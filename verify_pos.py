import nltk

try:
    print("Checking for averaged_perceptron_tagger_eng...")
    nltk.data.find('taggers/averaged_perceptron_tagger_eng')
    print("averaged_perceptron_tagger_eng found!")
    
    print("Testing POS tagging...")
    text = "Hello world"
    tokens = nltk.word_tokenize(text)
    tags = nltk.pos_tag(tokens)
    print(f"Tags: {tags}")
    
    if len(tags) > 0:
        print("SUCCESS: POS tagging working.")
    else:
        print("FAILURE: Unexpected tagging result.")

except LookupError:
    print("FAILURE: averaged_perceptron_tagger_eng not found.")
except Exception as e:
    print(f"FAILURE: {e}")
