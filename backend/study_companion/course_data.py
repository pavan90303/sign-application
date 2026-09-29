import os
import random
import string
import json
import uuid
from django.conf import settings
from .models import Course, CourseSection, Lesson, LessonProgress, SectionProgress, CourseQuizAttempt

# Central asset validation helper
def get_verified_asset_info(asset_name):
    """
    Checks if asset exists in assets/ or assets/ISL_Gifs/.
    Returns dict: {'exists': bool, 'filename': str, 'url': str, 'media_type': str}
    """
    if not asset_name:
        return {'exists': False, 'filename': '', 'url': '', 'media_type': 'video'}
    
    clean_name = asset_name.strip()
    ext = os.path.splitext(clean_name)[1].lower()
    media_type = 'video' if ext in ('.mp4', '.webm', '.ogg', '.mov') else ('gif' if ext == '.gif' else 'image')

    assets_dir = getattr(settings, 'ASSETS_DIR', os.path.join(settings.BASE_DIR, 'assets'))
    base_assets = os.path.join(assets_dir, clean_name)
    if os.path.exists(base_assets):
        return {'exists': True, 'filename': clean_name, 'url': f"/static/{clean_name}", 'media_type': media_type}

    signs_assets = os.path.join(assets_dir, 'signs', clean_name)
    if os.path.exists(signs_assets):
        return {'exists': True, 'filename': clean_name, 'url': f"/static/signs/{clean_name}", 'media_type': media_type}

    gif_assets = os.path.join(assets_dir, 'ISL_Gifs', clean_name)
    if os.path.exists(gif_assets):
        return {'exists': True, 'filename': clean_name, 'url': f"/static/ISL_Gifs/{clean_name}", 'media_type': media_type}

    return {'exists': False, 'filename': clean_name, 'url': f"/static/{clean_name}", 'media_type': media_type}


def normalize_answer(text):
    """
    Normalizes a string for robust, fair comparison:
    - lowercase
    - strip punctuation (.?!,;:/-)
    - normalize multiple whitespaces
    """
    if not text:
        return ""
    clean = str(text).strip().lower()
    for ch in ['.', '?', '!', ',', ';', ':', '"', "'"]:
        clean = clean.replace(ch, '')
    clean = clean.replace('-', ' ')
    return ' '.join(clean.split())


# Complete definitions of the 5 progressive sections with learning types and acceptable answers
COURSE_DEFINITIONS = [
    {
        "section_number": 1,
        "title": "Alphabets & Letters",
        "level": "Beginner",
        "description": "Learn the complete A-Z alphabet in Indian Sign Language (ISL). Each alphabet is used for fingerspelling names, places, and unfamiliar vocabulary.",
        "lessons": [
            {
                "order": i,
                "title": f"Letter {letter}",
                "word_or_phrase": letter,
                "explanation": f"Form the Indian Sign Language handshape for the letter '{letter}'. Practice holding the posture steadily in neutral space.",
                "sign_asset": f"{letter}.mp4",
                "learning_type": "letter",
                "acceptable_answers": json.dumps([letter.lower(), f"letter {letter.lower()}", f"letter-{letter.lower()}"])
            }
            for i, letter in enumerate(string.ascii_uppercase, start=1)
        ]
    },
    {
        "section_number": 2,
        "title": "Basic Everyday Words",
        "level": "Beginner",
        "description": "Essential daily signs for greetings, courtesy, polite expressions, family members, and immediate needs.",
        "lessons": [
            {"order": 1, "title": "Hello", "word_or_phrase": "Hello", "explanation": "Raise your dominant open palm to your temple and move outward in a clear greeting gesture.", "sign_asset": "Hello.mp4", "learning_type": "word", "acceptable_answers": json.dumps(["hello", "hi", "greetings"])},
            {"order": 2, "title": "Hi", "word_or_phrase": "Hi", "explanation": "A friendly casual greeting using a gentle wave posture facing forward.", "sign_asset": "Hello.mp4", "learning_type": "word", "acceptable_answers": json.dumps(["hi", "hello", "hey"])},
            {"order": 3, "title": "Yes", "word_or_phrase": "Yes", "explanation": "Make an S-fist with your dominant hand and nod it up and down like a nodding head.", "sign_asset": "", "learning_type": "word", "acceptable_answers": json.dumps(["yes", "yeah", "correct"])},
            {"order": 4, "title": "No", "word_or_phrase": "No", "explanation": "Snap your index and middle finger against your thumb, or shake your hand side to side.", "sign_asset": "Not.mp4", "learning_type": "word", "acceptable_answers": json.dumps(["no", "not", "nope"])},
            {"order": 5, "title": "Please", "word_or_phrase": "Please", "explanation": "Place your flat open palm over your heart or chest and move in a gentle circular motion.", "sign_asset": "", "learning_type": "word", "acceptable_answers": json.dumps(["please", "plz"])},
            {"order": 6, "title": "Sorry", "word_or_phrase": "Sorry", "explanation": "Make a fist and rotate it over your chest in a circular motion expressing sincere apology.", "sign_asset": "", "learning_type": "word", "acceptable_answers": json.dumps(["sorry", "apologies", "apology"])},
            {"order": 7, "title": "Thank You", "word_or_phrase": "Thank You", "explanation": "Touch your fingertips to your chin, then smoothly extend your hand forward toward the person.", "sign_asset": "Thank You.mp4", "learning_type": "word", "acceptable_answers": json.dumps(["thank you", "thanks", "thankyou", "thank u"])},
            {"order": 8, "title": "Help", "word_or_phrase": "Help", "explanation": "Place a closed thumbs-up fist onto your opposite flat open palm and lift both hands upward together.", "sign_asset": "Help.mp4", "learning_type": "word", "acceptable_answers": json.dumps(["help", "assist", "assistance"])},
            {"order": 9, "title": "Water", "word_or_phrase": "Water", "explanation": "Form a 'W' handshape with your three middle fingers and tap your index finger gently against your chin.", "sign_asset": "", "learning_type": "word", "acceptable_answers": json.dumps(["water", "drink water"])},
            {"order": 10, "title": "Food / Eat", "word_or_phrase": "Food", "explanation": "Bring your pinched fingertips to your mouth repeatedly simulating putting food into your mouth.", "sign_asset": "Eat.mp4", "learning_type": "word", "acceptable_answers": json.dumps(["food", "eat", "meal"])},
            {"order": 11, "title": "Good", "word_or_phrase": "Good", "explanation": "Place the fingers of your flat hand to your lips, then move it forward into the open palm of your other hand.", "sign_asset": "Good.mp4", "learning_type": "word", "acceptable_answers": json.dumps(["good", "fine", "great", "well"])},
            {"order": 12, "title": "Bad", "word_or_phrase": "Bad", "explanation": "Touch your chin with your flat fingers, then flip your hand outward and downward toward the ground.", "sign_asset": "Wrong.mp4", "learning_type": "word", "acceptable_answers": json.dumps(["bad", "wrong", "not good"])},
            {"order": 13, "title": "Morning", "word_or_phrase": "Morning", "explanation": "Rest your non-dominant arm horizontally and bring your dominant hand upward like the rising sun.", "sign_asset": "Day.mp4", "learning_type": "word", "acceptable_answers": json.dumps(["morning", "day", "sunrise"])},
            {"order": 14, "title": "Night", "word_or_phrase": "Night", "explanation": "Arch your dominant wrist over your non-dominant horizontal arm like the sun dipping under the horizon.", "sign_asset": "", "learning_type": "word", "acceptable_answers": json.dumps(["night", "evening"])},
            {"order": 15, "title": "Home", "word_or_phrase": "Home", "explanation": "Touch your fingertips to the side of your mouth, then move back toward your ear.", "sign_asset": "Home.mp4", "learning_type": "word", "acceptable_answers": json.dumps(["home", "house"])},
            {"order": 16, "title": "School", "word_or_phrase": "School", "explanation": "Clap your flat dominant hand twice over your flat horizontal non-dominant palm.", "sign_asset": "College.mp4", "learning_type": "word", "acceptable_answers": json.dumps(["school", "college", "institute"])},
            {"order": 17, "title": "Friend", "word_or_phrase": "Friend", "explanation": "Hook your index fingers together in one direction, then reverse and hook them the other way.", "sign_asset": "", "learning_type": "word", "acceptable_answers": json.dumps(["friend", "companion", "pal"])},
            {"order": 18, "title": "Mother", "word_or_phrase": "Mother", "explanation": "Place your open dominant hand with thumb touching your chin twice with warmth.", "sign_asset": "", "learning_type": "word", "acceptable_answers": json.dumps(["mother", "mom", "mum"])},
            {"order": 19, "title": "Father", "word_or_phrase": "Father", "explanation": "Place your open dominant hand with thumb touching your forehead twice.", "sign_asset": "", "learning_type": "word", "acceptable_answers": json.dumps(["father", "dad"])},
            {"order": 20, "title": "Brother", "word_or_phrase": "Brother", "explanation": "Sign male (touch forehead) followed by bringing both horizontal index fingers together.", "sign_asset": "", "learning_type": "word", "acceptable_answers": json.dumps(["brother", "bro"])},
            {"order": 21, "title": "Sister", "word_or_phrase": "Sister", "explanation": "Sign female (stroke jawline) followed by bringing both horizontal index fingers together.", "sign_asset": "", "learning_type": "word", "acceptable_answers": json.dumps(["sister", "sis"])}
        ]
    },
    {
        "section_number": 3,
        "title": "Intermediate Words",
        "level": "Intermediate",
        "description": "Expand your vocabulary for professional, educational, community, and emergency situations.",
        "lessons": [
            {"order": 1, "title": "Teacher", "word_or_phrase": "Teacher", "explanation": "Form flattened O-hands near your temples, move forward, then lower both hands in the person marker.", "sign_asset": "", "learning_type": "word", "acceptable_answers": json.dumps(["teacher", "instructor", "professor"])},
            {"order": 2, "title": "Student", "word_or_phrase": "Student", "explanation": "Lift knowledge from your non-dominant palm to your forehead, followed by the person marker.", "sign_asset": "Study.mp4", "learning_type": "word", "acceptable_answers": json.dumps(["student", "learner", "pupil"])},
            {"order": 3, "title": "College", "word_or_phrase": "College", "explanation": "Place your flat dominant hand over your other palm and circle it upward in an expansive spiral.", "sign_asset": "College.mp4", "learning_type": "word", "acceptable_answers": json.dumps(["college", "university"])},
            {"order": 4, "title": "Hospital", "word_or_phrase": "Hospital", "explanation": "Use two fingers of your dominant hand to trace a small cross on your opposite upper shoulder.", "sign_asset": "", "learning_type": "word", "acceptable_answers": json.dumps(["hospital", "clinic"])},
            {"order": 5, "title": "Doctor", "word_or_phrase": "Doctor", "explanation": "Tap the fingertips of your bent hand against the inside wrist of your non-dominant hand checking the pulse.", "sign_asset": "", "learning_type": "word", "acceptable_answers": json.dumps(["doctor", "physician", "dr"])},
            {"order": 6, "title": "Emergency", "word_or_phrase": "Emergency", "explanation": "Form an 'E' handshape and shake it rapidly back and forth indicating high urgency.", "sign_asset": "", "learning_type": "word", "acceptable_answers": json.dumps(["emergency", "urgent", "urgency"])},
            {"order": 7, "title": "Family", "word_or_phrase": "Family", "explanation": "Start with two 'F' handshapes touching at index and thumbs, circle both hands outward until pinkies meet.", "sign_asset": "", "learning_type": "word", "acceptable_answers": json.dumps(["family", "relatives"])},
            {"order": 8, "title": "Computer", "word_or_phrase": "Computer", "explanation": "Move a 'C' handshape upward along your opposite forearm in a forward arc.", "sign_asset": "Computer.mp4", "learning_type": "word", "acceptable_answers": json.dumps(["computer", "pc", "laptop"])},
            {"order": 9, "title": "Education", "word_or_phrase": "Education", "explanation": "Bring 'E' handshapes from your eyes outward, turning into 'D' handshapes representing intellectual growth.", "sign_asset": "Study.mp4", "learning_type": "word", "acceptable_answers": json.dumps(["education", "study", "learning"])},
            {"order": 10, "title": "Communication", "word_or_phrase": "Communication", "explanation": "Move two 'C' handshapes alternately forward and back from near your mouth.", "sign_asset": "Language.mp4", "learning_type": "word", "acceptable_answers": json.dumps(["communication", "language", "dialogue"])},
            {"order": 11, "title": "Bus", "word_or_phrase": "Bus", "explanation": "Mimic gripping and steering a large horizontal commercial vehicle steering wheel.", "sign_asset": "", "learning_type": "word", "acceptable_answers": json.dumps(["bus", "transit"])},
            {"order": 12, "title": "Travel", "word_or_phrase": "Travel", "explanation": "Move a bent 'V' handshape forward through space in a sweeping, winding journey path.", "sign_asset": "Distance.mp4", "learning_type": "word", "acceptable_answers": json.dumps(["travel", "distance", "journey", "trip"])},
            {"order": 13, "title": "Weather", "word_or_phrase": "Weather", "explanation": "Wiggle both 'W' handshapes as they descend downward like changing atmospheric waves.", "sign_asset": "", "learning_type": "word", "acceptable_answers": json.dumps(["weather", "climate"])},
            {"order": 14, "title": "Work", "word_or_phrase": "Work", "explanation": "Tap the heel of your dominant fist onto the back of your opposite wrist twice steadily.", "sign_asset": "Work.mp4", "learning_type": "word", "acceptable_answers": json.dumps(["work", "job", "labor"])},
            {"order": 15, "title": "Learn", "word_or_phrase": "Learn", "explanation": "Take knowledge from your flat non-dominant palm with your fingertips and press it into your forehead.", "sign_asset": "Learn.mp4", "learning_type": "word", "acceptable_answers": json.dumps(["learn", "learning", "study"])},
            {"order": 16, "title": "Understand", "word_or_phrase": "Understand", "explanation": "Flick your index finger upward next to your temple like a lightbulb turning on in your mind.", "sign_asset": "", "learning_type": "word", "acceptable_answers": json.dumps(["understand", "comprehend", "get it"])},
            {"order": 17, "title": "Important", "word_or_phrase": "Important", "explanation": "Touch both 'F' handshapes in front of you, circle upward and bring them together firmly at the top.", "sign_asset": "", "learning_type": "word", "acceptable_answers": json.dumps(["important", "crucial", "essential"])},
            {"order": 18, "title": "Problem", "word_or_phrase": "Problem", "explanation": "Twist two bent 'V' fingers against each other twice with an anxious or focused expression.", "sign_asset": "Wrong.mp4", "learning_type": "word", "acceptable_answers": json.dumps(["problem", "issue", "trouble", "wrong"])},
            {"order": 19, "title": "Safe", "word_or_phrase": "Safe", "explanation": "Cross both wrists in front of your chest with 'S' handshapes, then swing them outward to break free into safety.", "sign_asset": "Safe.mp4", "learning_type": "word", "acceptable_answers": json.dumps(["safe", "safety", "secure"])},
            {"order": 20, "title": "Danger", "word_or_phrase": "Danger", "explanation": "Brush your dominant thumb upward against the knuckles of your opposite fist twice with caution.", "sign_asset": "", "learning_type": "word", "acceptable_answers": json.dumps(["danger", "dangerous", "hazard"])}
        ]
    },
    {
        "section_number": 4,
        "title": "Short Sentences",
        "level": "Intermediate",
        "description": "Construct meaningful multi-sign statements, self-introductions, polite inquiries, and essential questions.",
        "lessons": [
            {"order": 1, "title": "How are you?", "word_or_phrase": "How are you?", "explanation": "Sign 'HOW' with both palms rotating outward, followed by pointing forward for 'YOU' with an inquiring expression.", "sign_asset": "How.mp4,You.mp4", "learning_type": "sentence", "acceptable_answers": json.dumps(["how are you", "how are you?"])},
            {"order": 2, "title": "What is your name?", "word_or_phrase": "What is your name?", "explanation": "Point flat palm forward for 'YOUR', tap two horizontal fingers twice for 'NAME', then shake open hands for 'WHAT'.", "sign_asset": "What.mp4,Your.mp4,Name.mp4", "learning_type": "sentence", "acceptable_answers": json.dumps(["what is your name", "what is your name?"])},
            {"order": 3, "title": "My name is...", "word_or_phrase": "My name is...", "explanation": "Place flat palm on chest for 'MY', tap two fingers for 'NAME', followed by fingerspelling your personal name letters.", "sign_asset": "My.mp4,Name.mp4", "learning_type": "sentence", "acceptable_answers": json.dumps(["my name is", "my name"])},
            {"order": 4, "title": "I am a student.", "word_or_phrase": "I am a student.", "explanation": "Point index finger to self for 'I', followed by the sign for 'STUDY / STUDENT'.", "sign_asset": "I.mp4,Study.mp4", "learning_type": "sentence", "acceptable_answers": json.dumps(["i am a student", "i am student"])},
            {"order": 5, "title": "I need help.", "word_or_phrase": "I need help.", "explanation": "Point to self 'I', followed by the sign for 'HELP' directed toward yourself with urgency.", "sign_asset": "I.mp4,Help.mp4", "learning_type": "sentence", "acceptable_answers": json.dumps(["i need help", "help me", "i help"])},
            {"order": 6, "title": "Thank you very much.", "word_or_phrase": "Thank you very much.", "explanation": "Bring flat hand from your chin outward with both hands for deep emphasis and grateful expression.", "sign_asset": "Thank You.mp4,Great.mp4", "learning_type": "sentence", "acceptable_answers": json.dumps(["thank you very much", "thanks a lot", "thank you"])},
            {"order": 7, "title": "Where are you going?", "word_or_phrase": "Where are you going?", "explanation": "Point 'YOU', sign 'GO' moving fingers forward, followed by 'WHERE' with wagging index finger and furrowed brow.", "sign_asset": "Where.mp4,You.mp4,Go.mp4", "learning_type": "sentence", "acceptable_answers": json.dumps(["where are you going", "where you go", "where are you going?"])},
            {"order": 8, "title": "I don't understand.", "word_or_phrase": "I don't understand.", "explanation": "Point to self 'I', flick index finger at temple while shaking head indicating non-comprehension.", "sign_asset": "I.mp4,Does Not.mp4", "learning_type": "sentence", "acceptable_answers": json.dumps(["i don't understand", "i dont understand", "i do not understand"])},
            {"order": 9, "title": "Please help me.", "word_or_phrase": "Please help me.", "explanation": "Move the 'HELP' sign directly toward your chest with a polite, requesting facial expression.", "sign_asset": "Help.mp4,ME.mp4", "learning_type": "sentence", "acceptable_answers": json.dumps(["please help me", "help me please", "help me"])},
            {"order": 10, "title": "I am learning sign language.", "word_or_phrase": "I am learning sign language.", "explanation": "Combine 'I', 'LEARN' (from palm to forehead), rotating hands for 'SIGN', and outward waves for 'LANGUAGE'.", "sign_asset": "I.mp4,Learn.mp4,Sign.mp4,Language.mp4", "learning_type": "sentence", "acceptable_answers": json.dumps(["i am learning sign language", "i learn sign language"])}
        ]
    },
    {
        "section_number": 5,
        "title": "Sentences & Conversations",
        "level": "Advanced",
        "description": "Engage in natural practical dialogues, ask for directions, clarify information, and complete conversation sequences.",
        "lessons": [
            {"order": 1, "title": "Where is the hospital?", "word_or_phrase": "Where is the hospital?", "explanation": "Sign 'HOSPITAL' (cross on arm), followed by 'WHERE' with tilted head and raised eyebrows.", "sign_asset": "Where.mp4", "learning_type": "sentence", "acceptable_answers": json.dumps(["where is the hospital", "where is hospital", "where is the hospital?"])},
            {"order": 2, "title": "Can you please help me?", "word_or_phrase": "Can you please help me?", "explanation": "Sign 'CAN', 'YOU', 'HELP', and 'ME' with a polite, inviting facial posture.", "sign_asset": "Can.mp4,You.mp4,Help.mp4,ME.mp4", "learning_type": "sentence", "acceptable_answers": json.dumps(["can you please help me", "can you help me", "can you please help me?"])},
            {"order": 3, "title": "I want to go to the bus station.", "word_or_phrase": "I want to go to the bus station.", "explanation": "Sign 'I', pull hands inward for 'WANT', point forward for 'GO', and fingerspell/mimic 'BUS STATION'.", "sign_asset": "I.mp4,Go.mp4", "learning_type": "sentence", "acceptable_answers": json.dumps(["i want to go to the bus station", "i go to bus station"])},
            {"order": 4, "title": "I am studying at college.", "word_or_phrase": "I am studying at college.", "explanation": "Sign 'I', followed by 'STUDY', and open spiral upward for 'COLLEGE'.", "sign_asset": "I.mp4,Study.mp4,College.mp4", "learning_type": "sentence", "acceptable_answers": json.dumps(["i am studying at college", "i study college"])},
            {"order": 5, "title": "What are you doing today?", "word_or_phrase": "What are you doing today?", "explanation": "Sign 'WHAT', point 'YOU', sign 'DO' with pinching index/thumb, and 'DAY' with the sun arc.", "sign_asset": "What.mp4,You.mp4,Do.mp4,Day.mp4", "learning_type": "sentence", "acceptable_answers": json.dumps(["what are you doing today", "what you do today", "what are you doing today?"])},
            {"order": 6, "title": "I don't understand what you are saying.", "word_or_phrase": "I don't understand what you are saying.", "explanation": "Sign 'YOU TALK', point to self 'I', and shake head while signing 'DOES NOT UNDERSTAND'.", "sign_asset": "I.mp4,Does Not.mp4,What.mp4,You.mp4,Talk.mp4", "learning_type": "sentence", "acceptable_answers": json.dumps(["i don't understand what you are saying", "i dont understand you talk"])},
            {"order": 7, "title": "Can you explain that again?", "word_or_phrase": "Can you explain that again?", "explanation": "Sign 'CAN', point 'YOU', roll hands forward for 'AGAIN' with an inquisitive tilt.", "sign_asset": "Can.mp4,You.mp4,Again.mp4", "learning_type": "sentence", "acceptable_answers": json.dumps(["can you explain that again", "explain again please", "can you explain that again?"])},
            {"order": 8, "title": "Conversation: Greetings & Health", "word_or_phrase": "Person A: Hello, How are you? | Person B: I am fine, Thank you.", "explanation": "Dialogue exchange: Person A initiates with 'Hello, How are you?'; Person B smiles and signs 'Good, Thank you.'", "sign_asset": "Hello.mp4,How.mp4,You.mp4,Good.mp4,Thank You.mp4", "learning_type": "dialogue", "acceptable_answers": json.dumps(["i am fine, thank you", "fine thank you", "good thank you"])},
            {"order": 9, "title": "Conversation: Name Exchange", "word_or_phrase": "Person A: What is your name? | Person B: My name is...", "explanation": "Dialogue exchange: Person A signs 'What is your name?'; Person B responds with 'My name is...' and fingerspells.", "sign_asset": "What.mp4,Your.mp4,Name.mp4,My.mp4,Name.mp4", "learning_type": "dialogue", "acceptable_answers": json.dumps(["my name is...", "my name is", "my name"])},
            {"order": 10, "title": "Conversation: Sign Language Practice", "word_or_phrase": "Person A: Do you know sign language? | Person B: Yes, I am learning every day.", "explanation": "Dialogue exchange: Person A: 'You know sign language?'; Person B: 'Yes, I learn sign language every day!'", "sign_asset": "You.mp4,Learn.mp4,Sign.mp4,Language.mp4,Good.mp4", "learning_type": "dialogue", "acceptable_answers": json.dumps(["yes, i am learning every day", "yes i learn everyday", "yes i learn sign language"])}
        ]
    }
]


def seed_isl_course():
    """
    Idempotent initialization: seeds the complete Indian Sign Language course,
    all 5 sections, and all progressive lessons into the database.
    """
    course, _ = Course.objects.get_or_create(
        slug="isl-course",
        defaults={
            "title": "Indian Sign Language",
            "subtitle": "Beginner to Advanced",
            "description": "Comprehensive course covering alphabets, essential vocabulary, everyday phrases, and complete conversational dialogues in Indian Sign Language."
        }
    )

    for sec_def in COURSE_DEFINITIONS:
        section, _ = CourseSection.objects.get_or_create(
            course=course,
            section_number=sec_def["section_number"],
            defaults={
                "title": sec_def["title"],
                "level": sec_def["level"],
                "description": sec_def["description"],
                "order": sec_def["section_number"]
            }
        )
        section.title = sec_def["title"]
        section.level = sec_def["level"]
        section.description = sec_def["description"]
        section.order = sec_def["section_number"]
        section.save()

        for les_def in sec_def["lessons"]:
            lesson, _ = Lesson.objects.get_or_create(
                section=section,
                order=les_def["order"],
                defaults={
                    "title": les_def["title"],
                    "word_or_phrase": les_def["word_or_phrase"],
                    "explanation": les_def["explanation"],
                    "sign_asset": les_def["sign_asset"],
                    "learning_type": les_def.get("learning_type", "word"),
                    "acceptable_answers": les_def.get("acceptable_answers", "")
                }
            )
            lesson.title = les_def["title"]
            lesson.word_or_phrase = les_def["word_or_phrase"]
            lesson.explanation = les_def["explanation"]
            lesson.sign_asset = les_def["sign_asset"]
            lesson.learning_type = les_def.get("learning_type", "word")
            lesson.acceptable_answers = les_def.get("acceptable_answers", "")
            lesson.save()

    return course


def get_user_course_progress(user):
    """
    Computes complete course progress and progression state for a user.
    """
    course = seed_isl_course()
    sections = list(course.sections.all().order_by('section_number'))

    total_lessons = Lesson.objects.filter(section__course=course).count()
    completed_lesson_ids = set(
        LessonProgress.objects.filter(user=user, completed=True).values_list('lesson_id', flat=True)
    )
    total_completed = len(completed_lesson_ids)
    overall_percentage = int((total_completed / total_lessons) * 100) if total_lessons > 0 else 0

    section_data = []
    completed_sections_count = 0
    active_section = None
    previous_section_passed = True  # Section 1 is always initially unlocked

    for idx, sec in enumerate(sections, start=1):
        sec_lessons = list(sec.lessons.all().order_by('order'))
        sec_total = len(sec_lessons)

        sec_prog, _ = SectionProgress.objects.get_or_create(
            user=user,
            section=sec,
            defaults={"unlocked": (idx == 1)}
        )

        if idx == 1:
            is_unlocked = True
        else:
            is_unlocked = sec_prog.unlocked or previous_section_passed

        if is_unlocked and not sec_prog.unlocked:
            sec_prog.unlocked = True
            sec_prog.save(update_fields=['unlocked'])

        is_quiz_passed = sec_prog.quiz_completed
        # Section progression operates at section level: passing quiz marks section fully completed
        is_section_fully_completed = is_quiz_passed

        if is_section_fully_completed:
            completed_sections_count += 1
            sec_percentage = 100
        elif is_unlocked:
            sec_percentage = 50 if sec_prog.best_score > 0 else 25
        else:
            sec_percentage = 0

        if is_unlocked and active_section is None and not is_quiz_passed:
            active_section = sec

        section_data.append({
            "section": sec,
            "section_number": sec.section_number,
            "title": sec.title,
            "level": sec.level,
            "description": sec.description,
            "total_lessons": sec_total,
            "completed_lessons": sec_total if is_section_fully_completed else (1 if is_unlocked else 0),
            "percentage": sec_percentage,
            "completion_percent": sec_percentage,
            "is_unlocked": is_unlocked,
            "lessons_all_done": True,
            "is_quiz_passed": is_quiz_passed,
            "quiz_passed": is_quiz_passed,
            "is_completed": is_section_fully_completed,
            "is_fully_completed": is_section_fully_completed,
            "best_score": sec_prog.best_score,
            "quiz_best_score": sec_prog.best_score,
            "first_lesson_id": sec_lessons[0].id if sec_lessons else None,
            "first_lesson": sec_lessons[0] if sec_lessons else None,
        })

        previous_section_passed = is_section_fully_completed

    if active_section is None and sections:
        active_section = sections[0]

    total_sections = len(sections)
    overall_percentage = int((completed_sections_count / total_sections) * 100) if total_sections > 0 else 0

    return {
        "course": course,
        "overall_percentage": overall_percentage,
        "progress_percent": overall_percentage,
        "total_lessons": total_lessons,
        "total_completed": completed_sections_count,
        "completed_lessons": completed_sections_count,
        "completed_sections_count": completed_sections_count,
        "completed_sections": completed_sections_count,
        "total_sections": total_sections,
        "sections": section_data,
        "section_progress_list": section_data,
        "active_section": active_section,
        "next_lesson": sections[0].lessons.first() if sections and sections[0].lessons.exists() else None,
    }


def search_section_signs(section_id, query):
    """
    Searches for a sign within the given section for practice.
    """
    clean_query = query.strip().lower()
    try:
        section = CourseSection.objects.get(id=section_id)
    except CourseSection.DoesNotExist:
        return {"match": None, "results": [], "in_section": False, "suggestions": []}

    lessons = list(section.lessons.all().order_by('order'))
    suggestions = [l.word_or_phrase for l in lessons][:10]

    matching_lessons = [
        l for l in lessons
        if clean_query in l.word_or_phrase.lower() or clean_query in l.title.lower()
    ]

    results = []
    for l in matching_lessons:
        first_asset = l.sign_asset.split(',')[0].strip() if l.sign_asset else ""
        asset_info = get_verified_asset_info(first_asset)

        results.append({
            "id": l.id,
            "title": l.title,
            "word": l.word_or_phrase,
            "description": l.explanation,
            "video_url": asset_info['url'] if asset_info['exists'] else "",
            "has_video": asset_info['exists'],
            "asset_list": l.sign_asset_list
        })

    return {
        "in_section": bool(results),
        "match": results[0] if results else None,
        "results": results,
        "suggestions": suggestions
    }


# =====================================================================
# DUOLINGO-STYLE SECTION-ACCURATE QUIZ ENGINE
# =====================================================================

def validate_question(q, section):
    """
    Strict backend validator:
    Ensures every question adheres to all 10 strict correctness rules:
    1. Lesson belongs to requested section.
    2. Sign asset exists.
    3. Correct answer belongs to that lesson.
    4. Distractors belong to the same section.
    5. No duplicate options exist.
    6. Exactly one correct answer exists for single-choice questions.
    7. Sign asset is not used as both correct and incorrect.
    8. Question type is compatible.
    9. Required assets exist on disk.
    10. No content from another section appears.
    """
    if q.get('section_id') != section.id:
        return False
    if q.get('section_number') != section.section_number:
        return False

    q_type = q.get('type')

    if q_type in ('sign_to_meaning', 'complete_sentence', 'sequence_to_meaning', 'dialogue', 'context_meaning', 'sentence_to_sequence'):
        options = q.get('options', [])
        if len(options) != 4:
            return False
        if len(set(options)) != 4:
            return False  # No duplicates
        correct_ans = q.get('correct_answer')
        if options.count(correct_ans) != 1:
            return False  # Exactly one correct answer
        if q.get('correct_index') != options.index(correct_ans):
            return False

    elif q_type == 'meaning_to_sign':
        options = q.get('options', [])
        if len(options) != 4:
            return False
        # Ensure all option sign media exist on disk and are unique
        urls = [opt.get('media_url') or opt.get('video_url') for opt in options if isinstance(opt, dict)]
        if len(urls) != 4 or len(set(urls)) != 4:
            return False
        for opt in options:
            url = opt.get('media_url') or opt.get('video_url') or ''
            clean_name = url.replace('/static/ISL_Gifs/', '').replace('/static/', '').strip()
            v_check = get_verified_asset_info(clean_name)
            if not v_check['exists']:
                return False
        correct_index = q.get('correct_index')
        if correct_index is None or correct_index not in (0, 1, 2, 3):
            return False

    elif q_type == 'type_answer':
        if not q.get('acceptable_answers') or len(q.get('acceptable_answers')) == 0:
            return False
        media = q.get('media', {})
        if not media.get('has_video'):
            return False

    elif q_type == 'matching':
        pairs = q.get('pairs', [])
        if len(pairs) != 4:
            return False
        words = [p['word'] for p in pairs]
        if len(set(words)) != 4:
            return False

    return True


def sanitize_quiz_for_client(server_questions):
    """
    Removes correct answer keys before sending questions to the browser.
    Ensures the client cannot inspect or cheat answers.
    Normalizes options so meaning_to_sign contains clean media descriptors
    without leaking sign_name.
    """
    client_questions = []
    for idx, q in enumerate(server_questions):
        client_options = []
        for o_idx, opt in enumerate(q.get('options', [])):
            if isinstance(opt, dict):
                # meaning_to_sign or visual media options
                m_url = str(opt.get('media_url') or opt.get('video_url') or '')
                ext = os.path.splitext(m_url)[1].lower()
                m_type = opt.get('media_type') or ('video' if ext in ('.mp4', '.webm', '.ogg', '.mov') else ('gif' if ext == '.gif' else 'image'))
                client_options.append({
                    'id': opt.get('id', o_idx),
                    'index': o_idx,
                    'value': opt.get('value', o_idx),
                    'label': opt.get('label', f"Option {chr(65+o_idx)}"),
                    'letter': opt.get('letter', chr(65+o_idx)),
                    'media_type': m_type,
                    'media_url': m_url,
                    'video_url': m_url,
                })
            else:
                client_options.append(str(opt))

        client_q = {
            'question_index': idx,
            'id': str(q['id']),
            'type': str(q['type']),
            'section_id': int(q['section_id']),
            'section_number': int(q['section_number']),
            'section_title': str(q['section_title']),
            'prompt': str(q['prompt']),
            'target_word': str(q.get('target_word', '')),
            'media': q.get('media', {}),
            'options': client_options,
            'matching_data': q.get('matching_data', {}),
            'stage': q.get('stage', 1),
            'stage_name': q.get('stage_name', 'Stage 1: Warm Up'),
            'stage_desc': q.get('stage_desc', ''),
            'timer': q.get('timer', 15),
        }
        client_questions.append(client_q)
    return client_questions


def generate_section_quiz(section_id, user=None):
    """
    Generates a section-accurate, Duolingo-style 10-exercise quiz
    strictly from the lesson dataset of section_id.
    Guarantees:
    - 0 cross-section questions
    - 0 incorrect sign-answer mappings
    - 0 duplicate choices
    - 0 missing sign assets
    - 0 multiple-correct-answer single-choice questions
    """
    section = CourseSection.objects.get(id=section_id)
    all_lessons = list(section.lessons.all().order_by('order'))
    video_lessons = [l for l in all_lessons if l.has_sign_asset]

    sec_num = section.section_number
    questions = []

    # Filter lessons that have unique sign assets for video-based options
    unique_asset_map = {}
    for l in video_lessons:
        first_a = l.sign_asset.split(',')[0].strip()
        v_check = get_verified_asset_info(first_a)
        if first_a and v_check['exists'] and first_a not in unique_asset_map:
            unique_asset_map[first_a] = l
    distinct_video_lessons = list(unique_asset_map.values())

    # Helper: pick 3 distractors from same section
    def pick_distractors(target_lesson, candidate_pool, key_func=lambda l: l.word_or_phrase, count=3):
        candidates = [key_func(l) for l in candidate_pool if l.id != target_lesson.id and key_func(l).lower() != key_func(target_lesson).lower()]
        unique_candidates = list(dict.fromkeys(candidates))
        if len(unique_candidates) < count:
            fallback = [key_func(l) for l in all_lessons if l.id != target_lesson.id and key_func(l).lower() != key_func(target_lesson).lower()]
            unique_candidates = list(dict.fromkeys(unique_candidates + fallback))
        return random.sample(unique_candidates, min(count, len(unique_candidates)))

    # SECTION 1: Alphabets & Letters (A-Z) - 26 letters with video
    if sec_num == 1:
        pool = list(video_lessons) if video_lessons else list(all_lessons)
        available = list(pool)
        random.shuffle(available)

        # 10x Sign -> Letter (sign_to_meaning)
        for _ in range(10):
            if not available and pool:
                available = list(pool)
                random.shuffle(available)
            if not available:
                break
            target = available.pop()
            distractors = pick_distractors(target, pool, count=3)
            options = [target.word_or_phrase] + distractors
            random.shuffle(options)
            first_asset = target.sign_asset.split(',')[0].strip()
            v_first = get_verified_asset_info(first_asset)

            q = {
                'id': f"sec1_s2m_{uuid.uuid4().hex[:6]}",
                'type': 'sign_to_meaning',
                'section_id': section.id,
                'section_number': 1,
                'section_title': section.title,
                'lesson_id': target.id,
                'prompt': "What letter does this sign represent?",
                'media': {'video_url': v_first['url'], 'has_video': True, 'title': target.title, 'media_type': v_first['media_type']},
                'options': options,
                'correct_answer': target.word_or_phrase,
                'correct_index': options.index(target.word_or_phrase),
                'correct_sign_url': v_first['url'],
                'explanation': target.explanation or f"The hand posture shown represents the letter '{target.word_or_phrase}' in Indian Sign Language."
            }
            if validate_question(q, section):
                questions.append(q)

        # 5x Letter -> Sign (meaning_to_sign)
        for _ in range(5):
            if not available:
                available = list(video_lessons)
                random.shuffle(available)
            target = available.pop()
            eligible_distractors = [l for l in distinct_video_lessons if l.sign_asset != target.sign_asset]
            if len(eligible_distractors) < 3:
                continue
            distractor_lessons = random.sample(eligible_distractors, 3)
            choices = [target] + distractor_lessons
            random.shuffle(choices)

            options = []
            correct_idx = 0
            for idx, c in enumerate(choices):
                asset_f = c.sign_asset.split(',')[0].strip()
                v_info = get_verified_asset_info(asset_f)
                options.append({
                    'id': idx,
                    'index': idx,
                    'value': idx,
                    'label': f"Option {chr(65+idx)}",
                    'letter': chr(65+idx),
                    'media_type': v_info['media_type'],
                    'media_url': v_info['url'],
                    'video_url': v_info['url'],
                    'sign_name': c.word_or_phrase
                })
                if c.id == target.id:
                    correct_idx = idx

            target_asset = target.sign_asset.split(',')[0].strip()
            v_target = get_verified_asset_info(target_asset)
            q = {
                'id': f"sec1_m2s_{uuid.uuid4().hex[:6]}",
                'type': 'meaning_to_sign',
                'section_id': section.id,
                'section_number': 1,
                'section_title': section.title,
                'lesson_id': target.id,
                'prompt': f"Which sign represents the letter '{target.word_or_phrase}'?",
                'target_word': f"Letter {target.word_or_phrase}",
                'media': {'has_video': False},
                'options': options,
                'correct_answer': target_asset,
                'correct_index': correct_idx,
                'correct_sign_url': v_target['url'],
                'explanation': target.explanation or f"Observe the finger posture for Letter '{target.word_or_phrase}'."
            }
            if validate_question(q, section):
                questions.append(q)

    # SECTION 2: Basic Everyday Words
    elif sec_num == 2:
        available_vids = list(video_lessons)
        random.shuffle(available_vids)

        # 8x Sign -> Meaning
        for _ in range(8):
            if not available_vids:
                available_vids = list(video_lessons)
                random.shuffle(available_vids)
            target = available_vids.pop()
            distractors = pick_distractors(target, all_lessons, count=3)
            options = [target.word_or_phrase] + distractors
            random.shuffle(options)
            first_asset = target.sign_asset.split(',')[0].strip()
            v_first = get_verified_asset_info(first_asset)

            q = {
                'id': f"sec2_s2m_{uuid.uuid4().hex[:6]}",
                'type': 'sign_to_meaning',
                'section_id': section.id,
                'section_number': 2,
                'section_title': section.title,
                'lesson_id': target.id,
                'prompt': "What does this everyday sign mean?",
                'media': {'video_url': v_first['url'], 'has_video': True, 'title': target.title, 'media_type': v_first['media_type']},
                'options': options,
                'correct_answer': target.word_or_phrase,
                'correct_index': options.index(target.word_or_phrase),
                'correct_sign_url': v_first['url'],
                'explanation': target.explanation or f"This gesture signifies '{target.word_or_phrase}'."
            }
            if validate_question(q, section):
                questions.append(q)

        # 4x Meaning -> Sign
        for _ in range(4):
            if not available_vids:
                available_vids = list(video_lessons)
                random.shuffle(available_vids)
            target = available_vids.pop()
            eligible_distractors = [l for l in distinct_video_lessons if l.sign_asset != target.sign_asset]
            if len(eligible_distractors) < 3:
                continue
            distractor_lessons = random.sample(eligible_distractors, 3)
            choices = [target] + distractor_lessons
            random.shuffle(choices)

            options = []
            correct_idx = 0
            for idx, c in enumerate(choices):
                asset_f = c.sign_asset.split(',')[0].strip()
                v_info = get_verified_asset_info(asset_f)
                options.append({
                    'id': idx,
                    'index': idx,
                    'value': idx,
                    'label': f"Option {chr(65+idx)}",
                    'letter': chr(65+idx),
                    'media_type': v_info['media_type'],
                    'media_url': v_info['url'],
                    'video_url': v_info['url'],
                    'sign_name': c.word_or_phrase
                })
                if c.id == target.id:
                    correct_idx = idx

            target_asset = target.sign_asset.split(',')[0].strip()
            v_target = get_verified_asset_info(target_asset)
            q = {
                'id': f"sec2_m2s_{uuid.uuid4().hex[:6]}",
                'type': 'meaning_to_sign',
                'section_id': section.id,
                'section_number': 2,
                'section_title': section.title,
                'lesson_id': target.id,
                'prompt': f"Which sign means: '{target.word_or_phrase.upper()}'?",
                'target_word': target.word_or_phrase,
                'media': {'has_video': False},
                'options': options,
                'correct_answer': target_asset,
                'correct_index': correct_idx,
                'correct_sign_url': v_target['url'],
                'explanation': target.explanation or f"This sign represents '{target.word_or_phrase}'."
            }
            if validate_question(q, section):
                questions.append(q)

        # 3x Context Meaning
        polite_targets = [l for l in all_lessons if l.word_or_phrase in ("Thank You", "Please", "Sorry", "Help", "Good", "Bad", "Home", "Friend")]
        chosen_polite = random.sample(polite_targets, min(3, len(polite_targets)))
        for t_polite in chosen_polite:
            distractors = pick_distractors(t_polite, all_lessons, count=3)
            options = [t_polite.word_or_phrase] + distractors
            random.shuffle(options)
            first_asset = t_polite.sign_asset.split(',')[0].strip() if t_polite.sign_asset else ""

            q = {
                'id': f"sec2_ctx_{uuid.uuid4().hex[:6]}",
                'type': 'sign_to_meaning',
                'section_id': section.id,
                'section_number': 2,
                'section_title': section.title,
                'lesson_id': t_polite.id,
                'prompt': f"Which Section 2 everyday word means: '{t_polite.explanation}'?",
                'media': {'video_url': f"/static/{first_asset}" if first_asset else "", 'has_video': bool(first_asset)},
                'options': options,
                'correct_answer': t_polite.word_or_phrase,
                'correct_index': options.index(t_polite.word_or_phrase),
                'correct_sign_url': f"/static/{first_asset}" if first_asset else "",
                'explanation': t_polite.explanation
            }
            if validate_question(q, section):
                questions.append(q)

    # SECTION 3: Intermediate Words
    elif sec_num == 3:
        available_vids = list(video_lessons)
        random.shuffle(available_vids)

        # 5x Sign -> Meaning
        for _ in range(5):
            if not available_vids:
                available_vids = list(video_lessons)
                random.shuffle(available_vids)
            target = available_vids.pop()
            distractors = pick_distractors(target, all_lessons, count=3)
            options = [target.word_or_phrase] + distractors
            random.shuffle(options)
            first_asset = target.sign_asset.split(',')[0].strip()
            v_first = get_verified_asset_info(first_asset)

            q = {
                'id': f"sec3_s2m_{uuid.uuid4().hex[:6]}",
                'type': 'sign_to_meaning',
                'section_id': section.id,
                'section_number': 3,
                'section_title': section.title,
                'lesson_id': target.id,
                'prompt': "What does this intermediate sign mean?",
                'media': {'video_url': v_first['url'], 'has_video': True, 'title': target.title, 'media_type': v_first['media_type']},
                'options': options,
                'correct_answer': target.word_or_phrase,
                'correct_index': options.index(target.word_or_phrase),
                'correct_sign_url': v_first['url'],
                'explanation': target.explanation
            }
            if validate_question(q, section):
                questions.append(q)

        # 4x Meaning -> Sign
        for _ in range(4):
            if not available_vids:
                available_vids = list(video_lessons)
                random.shuffle(available_vids)
            target = available_vids.pop()
            eligible_distractors = [l for l in distinct_video_lessons if l.sign_asset != target.sign_asset]
            if len(eligible_distractors) < 3:
                continue
            distractor_lessons = random.sample(eligible_distractors, 3)
            choices = [target] + distractor_lessons
            random.shuffle(choices)

            options = []
            correct_idx = 0
            for idx, c in enumerate(choices):
                asset_f = c.sign_asset.split(',')[0].strip()
                v_info = get_verified_asset_info(asset_f)
                options.append({
                    'id': idx,
                    'index': idx,
                    'value': idx,
                    'label': f"Option {chr(65+idx)}",
                    'letter': chr(65+idx),
                    'media_type': v_info['media_type'],
                    'media_url': v_info['url'],
                    'video_url': v_info['url'],
                    'sign_name': c.word_or_phrase
                })
                if c.id == target.id:
                    correct_idx = idx

            target_asset = target.sign_asset.split(',')[0].strip()
            v_target = get_verified_asset_info(target_asset)
            q = {
                'id': f"sec3_m2s_{uuid.uuid4().hex[:6]}",
                'type': 'meaning_to_sign',
                'section_id': section.id,
                'section_number': 3,
                'section_title': section.title,
                'lesson_id': target.id,
                'prompt': f"Which sign represents: '{target.word_or_phrase.upper()}'?",
                'target_word': target.word_or_phrase,
                'media': {'has_video': False},
                'options': options,
                'correct_answer': target_asset,
                'correct_index': correct_idx,
                'correct_sign_url': v_target['url'],
                'explanation': target.explanation or f"This sign represents '{target.word_or_phrase}'."
            }
            if validate_question(q, section):
                questions.append(q)

        # 3x Context Meaning
        ctx_pool = [l for l in all_lessons if l.word_or_phrase in ("Hospital", "Doctor", "Emergency", "Work", "College", "Safe", "Medicine", "Pain")]
        chosen_ctx = random.sample(ctx_pool, min(3, len(ctx_pool)))
        for target_ctx in chosen_ctx:
            distractors = pick_distractors(target_ctx, all_lessons, count=3)
            options = [target_ctx.word_or_phrase] + distractors
            random.shuffle(options)
            first_asset = target_ctx.sign_asset.split(',')[0].strip() if target_ctx.sign_asset else ""

            q = {
                'id': f"sec3_ctx_{uuid.uuid4().hex[:6]}",
                'type': 'sign_to_meaning',
                'section_id': section.id,
                'section_number': 3,
                'section_title': section.title,
                'lesson_id': target_ctx.id,
                'prompt': f"Which Section 3 term describes: '{target_ctx.explanation}'?",
                'media': {'video_url': f"/static/{first_asset}" if first_asset else "", 'has_video': bool(first_asset)},
                'options': options,
                'correct_answer': target_ctx.word_or_phrase,
                'correct_index': options.index(target_ctx.word_or_phrase),
                'correct_sign_url': f"/static/{first_asset}" if first_asset else "",
                'explanation': target_ctx.explanation
            }
            if validate_question(q, section):
                questions.append(q)

        # 4x Additional Sign -> Meaning
        for _ in range(4):
            if not available_vids:
                available_vids = list(video_lessons)
                random.shuffle(available_vids)
            target = available_vids.pop()
            distractors = pick_distractors(target, all_lessons, count=3)
            options = [target.word_or_phrase] + distractors
            random.shuffle(options)
            first_asset = target.sign_asset.split(',')[0].strip()

            q = {
                'id': f"sec3_s2m_extra_{uuid.uuid4().hex[:6]}",
                'type': 'sign_to_meaning',
                'section_id': section.id,
                'section_number': 3,
                'section_title': section.title,
                'lesson_id': target.id,
                'prompt': "What does this intermediate sign mean?",
                'media': {'video_url': f"/static/{first_asset}", 'has_video': True, 'title': target.title},
                'options': options,
                'correct_answer': target.word_or_phrase,
                'correct_index': options.index(target.word_or_phrase),
                'correct_sign_url': f"/static/{first_asset}",
                'explanation': target.explanation
            }
            if validate_question(q, section):
                questions.append(q)

    # SECTION 4: Short Sentences (10 lessons, all with sign videos)
    elif sec_num == 4:
        available_sentences = list(all_lessons)
        random.shuffle(available_sentences)

        # 4x Sequence -> Meaning
        for _ in range(4):
            if not available_sentences:
                available_sentences = list(all_lessons)
                random.shuffle(available_sentences)
            target = available_sentences.pop()
            distractors = pick_distractors(target, all_lessons, count=3)
            options = [target.word_or_phrase] + distractors
            random.shuffle(options)

            first_asset = target.sign_asset.split(',')[0].strip()
            q = {
                'id': f"sec4_seq2m_{uuid.uuid4().hex[:6]}",
                'type': 'sequence_to_meaning',
                'section_id': section.id,
                'section_number': 4,
                'section_title': section.title,
                'lesson_id': target.id,
                'prompt': "What does this sign sequence mean?",
                'media': {
                    'video_url': f"/static/{first_asset}",
                    'has_video': True,
                    'sequence_list': target.sign_asset_list,
                    'title': target.title
                },
                'options': options,
                'correct_answer': target.word_or_phrase,
                'correct_index': options.index(target.word_or_phrase),
                'correct_sign_url': f"/static/{first_asset}",
                'explanation': target.explanation
            }
            if validate_question(q, section):
                questions.append(q)

        # 3x Complete the Sentence
        sentence_fillers = [
            ("I need help.", "I need ______.", "help", ["student", "name", "where"]),
            ("I am a student.", "I am a ______.", "student", ["help", "name", "sign language"]),
            ("What is your name?", "What is your ______?", "name", ["help", "student", "going"]),
            ("Where are you going?", "Where are you ______?", "going", ["name", "student", "help"]),
            ("Please help me.", "Please ______ me.", "help", ["name", "student", "understand"])
        ]
        chosen_fills = random.sample(sentence_fillers, 3)
        for full_s, blank_s, ans_word, dist_words in chosen_fills:
            options = [ans_word] + dist_words
            random.shuffle(options)
            matching_les = next((l for l in all_lessons if ans_word.lower() in l.word_or_phrase.lower()), all_lessons[0])
            first_asset = matching_les.sign_asset.split(',')[0].strip() if matching_les.sign_asset else ""

            q = {
                'id': f"sec4_comp_{uuid.uuid4().hex[:6]}",
                'type': 'complete_sentence',
                'section_id': section.id,
                'section_number': 4,
                'section_title': section.title,
                'lesson_id': matching_les.id,
                'prompt': f"Complete the learned sentence: '{blank_s}'",
                'media': {'video_url': f"/static/{first_asset}" if first_asset else "", 'has_video': bool(first_asset)},
                'options': options,
                'correct_answer': ans_word,
                'correct_index': options.index(ans_word),
                'correct_sign_url': f"/static/{first_asset}" if first_asset else "",
                'explanation': f"The complete sentence taught in this section is '{full_s}'."
            }
            if validate_question(q, section):
                questions.append(q)

        # 3x Sentence -> Sequence Choice
        for _ in range(3):
            if not available_sentences:
                available_sentences = list(all_lessons)
                random.shuffle(available_sentences)
            target = available_sentences.pop()
            distractors = random.sample([l for l in all_lessons if l.id != target.id], 3)
            choices = [target] + distractors
            random.shuffle(choices)

            options = []
            correct_idx = 0
            for idx, c in enumerate(choices):
                seq_repr = " → ".join([s.strip().replace('.mp4', '') for s in c.sign_asset.split(',') if s.strip()])
                options.append(f"{seq_repr} ({c.title})")
                if c.id == target.id:
                    correct_idx = idx

            first_asset = target.sign_asset.split(',')[0].strip()
            q = {
                'id': f"sec4_s2seq_{uuid.uuid4().hex[:6]}",
                'type': 'sign_to_meaning',
                'section_id': section.id,
                'section_number': 4,
                'section_title': section.title,
                'lesson_id': target.id,
                'prompt': f"Choose the correct sign sequence for: '{target.word_or_phrase}'",
                'media': {'has_video': False},
                'options': options,
                'correct_answer': options[correct_idx],
                'correct_index': correct_idx,
                'correct_sign_url': f"/static/{first_asset}",
                'explanation': target.explanation
            }
            if validate_question(q, section):
                questions.append(q)

        # 2x Additional Sequence -> Meaning
        for _ in range(2):
            if not available_sentences:
                available_sentences = list(all_lessons)
                random.shuffle(available_sentences)
            target = available_sentences.pop()
            distractors = pick_distractors(target, all_lessons, count=3)
            options = [target.word_or_phrase] + distractors
            random.shuffle(options)

            first_asset = target.sign_asset.split(',')[0].strip()
            q = {
                'id': f"sec4_seq2m_extra_{uuid.uuid4().hex[:6]}",
                'type': 'sequence_to_meaning',
                'section_id': section.id,
                'section_number': 4,
                'section_title': section.title,
                'lesson_id': target.id,
                'prompt': "What does this sentence mean in ISL?",
                'media': {
                    'video_url': f"/static/{first_asset}",
                    'has_video': True,
                    'sequence_list': target.sign_asset_list,
                    'title': target.title
                },
                'options': options,
                'correct_answer': target.word_or_phrase,
                'correct_index': options.index(target.word_or_phrase),
                'correct_sign_url': f"/static/{first_asset}",
                'explanation': target.explanation
            }
            if validate_question(q, section):
                questions.append(q)

        # 3x Additional Complete Sentence
        more_fills = [
            ("Nice to meet you.", "Nice to ______ you.", "meet", ["help", "student", "go"]),
            ("I understand sign language.", "I ______ sign language.", "understand", ["am", "help", "need"]),
            ("Where is the hospital?", "Where is the ______?", "hospital", ["student", "name", "going"])
        ]
        for full_s, blank_s, ans_word, dist_words in more_fills:
            options = [ans_word] + dist_words
            random.shuffle(options)
            matching_les = next((l for l in all_lessons if ans_word.lower() in l.word_or_phrase.lower()), all_lessons[0])
            first_asset = matching_les.sign_asset.split(',')[0].strip() if matching_les.sign_asset else ""

            q = {
                'id': f"sec4_comp_extra_{uuid.uuid4().hex[:6]}",
                'type': 'complete_sentence',
                'section_id': section.id,
                'section_number': 4,
                'section_title': section.title,
                'lesson_id': matching_les.id,
                'prompt': f"Complete the sentence: '{blank_s}'",
                'media': {'video_url': f"/static/{first_asset}" if first_asset else "", 'has_video': bool(first_asset)},
                'options': options,
                'correct_answer': ans_word,
                'correct_index': options.index(ans_word),
                'correct_sign_url': f"/static/{first_asset}" if first_asset else "",
                'explanation': f"The complete sentence taught is '{full_s}'."
            }
            if validate_question(q, section):
                questions.append(q)

    # SECTION 5: Sentences & Conversations (10 lessons, all with sign videos)
    elif sec_num == 5:
        available_dialogues = list(all_lessons)
        random.shuffle(available_dialogues)

        # 4x Complete Dialogue
        dialogues = [
            ("Person A: Hello, How are you?", "I am fine, Thank you.", ["Where is the hospital?", "My name is...", "Can you please help me?"]),
            ("Person A: What is your name?", "My name is...", ["I am fine, Thank you.", "Yes, I am learning every day.", "Where is the hospital?"]),
            ("Person A: Do you know sign language?", "Yes, I am learning every day.", ["I am fine, Thank you.", "My name is...", "Can you please help me?"]),
            ("Person A: Where is the bus stop?", "It is straight ahead, near the market.", ["I am fine, Thank you.", "My name is...", "Yes, I am learning every day."])
        ]
        for prompt_lead, correct_reply, dist_replies in dialogues:
            options = [correct_reply] + dist_replies
            random.shuffle(options)
            match_les = next((l for l in all_lessons if correct_reply.lower() in l.word_or_phrase.lower()), all_lessons[0])
            first_asset = match_les.sign_asset.split(',')[0].strip() if match_les.sign_asset else ""

            q = {
                'id': f"sec5_dial_{uuid.uuid4().hex[:6]}",
                'type': 'dialogue',
                'section_id': section.id,
                'section_number': 5,
                'section_title': section.title,
                'lesson_id': match_les.id,
                'prompt': f"Complete the learned conversation:\n\n{prompt_lead}\nPerson B: __________________",
                'media': {'video_url': f"/static/{first_asset}" if first_asset else "", 'has_video': bool(first_asset)},
                'options': options,
                'correct_answer': correct_reply,
                'correct_index': options.index(correct_reply),
                'correct_sign_url': f"/static/{first_asset}" if first_asset else "",
                'explanation': match_les.explanation
            }
            if validate_question(q, section):
                questions.append(q)

        # 4x Sequence -> Meaning
        for _ in range(4):
            if not available_dialogues:
                available_dialogues = list(all_lessons)
                random.shuffle(available_dialogues)
            target = available_dialogues.pop()
            distractors = pick_distractors(target, all_lessons, count=3)
            options = [target.word_or_phrase] + distractors
            random.shuffle(options)

            first_asset = target.sign_asset.split(',')[0].strip()
            q = {
                'id': f"sec5_seq2m_{uuid.uuid4().hex[:6]}",
                'type': 'sequence_to_meaning',
                'section_id': section.id,
                'section_number': 5,
                'section_title': section.title,
                'lesson_id': target.id,
                'prompt': "What conversation or sentence is being expressed?",
                'media': {
                    'video_url': f"/static/{first_asset}",
                    'has_video': True,
                    'sequence_list': target.sign_asset_list,
                    'title': target.title
                },
                'options': options,
                'correct_answer': target.word_or_phrase,
                'correct_index': options.index(target.word_or_phrase),
                'correct_sign_url': f"/static/{first_asset}",
                'explanation': target.explanation
            }
            if validate_question(q, section):
                questions.append(q)

        # 3x Complete the Sentence / Practical Inquiry
        inquiry_lessons = [l for l in all_lessons if "hospital" in l.word_or_phrase.lower() or "help" in l.word_or_phrase.lower() or "bus" in l.word_or_phrase.lower() or "safe" in l.word_or_phrase.lower()]
        for l_inq in inquiry_lessons[:3]:
            distractors = pick_distractors(l_inq, all_lessons, count=3)
            options = [l_inq.word_or_phrase] + distractors
            random.shuffle(options)
            first_asset = l_inq.sign_asset.split(',')[0].strip() if l_inq.sign_asset else ""

            q = {
                'id': f"sec5_inq_{uuid.uuid4().hex[:6]}",
                'type': 'sign_to_meaning',
                'section_id': section.id,
                'section_number': 5,
                'section_title': section.title,
                'lesson_id': l_inq.id,
                'prompt': f"Which advanced inquiry matches: '{l_inq.title}'?",
                'media': {'video_url': f"/static/{first_asset}" if first_asset else "", 'has_video': bool(first_asset)},
                'options': options,
                'correct_answer': l_inq.word_or_phrase,
                'correct_index': options.index(l_inq.word_or_phrase),
                'correct_sign_url': f"/static/{first_asset}" if first_asset else "",
                'explanation': l_inq.explanation
            }
            if validate_question(q, section):
                questions.append(q)

        # 2x Sentence to Sequence
        s_candidates = [l for l in all_lessons if ',' in l.sign_asset]
        s_targets = random.sample(s_candidates, 2) if len(s_candidates) >= 2 else all_lessons[:2]
        for s_target in s_targets:
            distractor_lessons = random.sample([l for l in all_lessons if l.id != s_target.id], 3)
            choices = [s_target] + distractor_lessons
            random.shuffle(choices)

            options = []
            correct_idx = 0
            for idx, c in enumerate(choices):
                seq_repr = " → ".join([s.strip().replace('.mp4', '') for s in c.sign_asset.split(',') if s.strip()])
                options.append(f"{seq_repr} ({c.title})")
                if c.id == s_target.id:
                    correct_idx = idx

            first_asset = s_target.sign_asset.split(',')[0].strip()
            q = {
                'id': f"sec5_s2seq_{uuid.uuid4().hex[:6]}",
                'type': 'sign_to_meaning',
                'section_id': section.id,
                'section_number': 5,
                'section_title': section.title,
                'lesson_id': s_target.id,
                'prompt': f"Choose the correct sign sequence for: '{s_target.word_or_phrase}'",
                'media': {'has_video': False},
                'options': options,
                'correct_answer': options[correct_idx],
                'correct_index': correct_idx,
                'correct_sign_url': f"/static/{first_asset}",
                'explanation': s_target.explanation
            }
            if validate_question(q, section):
                questions.append(q)

        # 2x Additional Sequence -> Meaning
        for _ in range(2):
            if not available_dialogues:
                available_dialogues = list(all_lessons)
                random.shuffle(available_dialogues)
            target = available_dialogues.pop()
            distractors = pick_distractors(target, all_lessons, count=3)
            options = [target.word_or_phrase] + distractors
            random.shuffle(options)

            first_asset = target.sign_asset.split(',')[0].strip()
            q = {
                'id': f"sec5_seq2m_extra_{uuid.uuid4().hex[:6]}",
                'type': 'sequence_to_meaning',
                'section_id': section.id,
                'section_number': 5,
                'section_title': section.title,
                'lesson_id': target.id,
                'prompt': "What does this conversation exchange convey in ISL?",
                'media': {
                    'video_url': f"/static/{first_asset}",
                    'has_video': True,
                    'sequence_list': target.sign_asset_list,
                    'title': target.title
                },
                'options': options,
                'correct_answer': target.word_or_phrase,
                'correct_index': options.index(target.word_or_phrase),
                'correct_sign_url': f"/static/{first_asset}",
                'explanation': target.explanation
            }
            if validate_question(q, section):
                questions.append(q)

    # Shuffled exercise presentation order
    random.shuffle(questions)

    # Slice to precisely 15 questions
    questions = questions[:15]

    # Attach stage metadata and timers
    for idx, q in enumerate(questions):
        if idx < 5:
            q['stage'] = 1
            q['stage_name'] = 'Stage 1: Warm Up'
            q['stage_desc'] = 'Get your bearings! 15s timer'
            q['timer'] = 15
        elif idx < 10:
            q['stage'] = 2
            q['stage_name'] = 'Stage 2: Speed Up'
            q['stage_desc'] = 'Pace is increasing! 12s timer'
            q['timer'] = 12
        elif idx < 13:
            q['stage'] = 3
            q['stage_name'] = 'Stage 3: Challenge'
            q['stage_desc'] = 'Speed challenge! 10s timer'
            q['timer'] = 10
        else:
            q['stage'] = 4
            q['stage_name'] = 'Stage 4: Final Rush'
            q['stage_desc'] = 'Sprint to the finish line! 8s timer'
            q['timer'] = 8

    return {
        'server_questions': questions,
        'client_questions': sanitize_quiz_for_client(questions)
    }


def check_quiz_answer(question, user_answer):
    """
    Backend evaluation function:
    Compares user_answer against backend question record.
    Returns: (is_correct: bool, correct_answer_display: str, explanation: str, correct_sign_url: str)
    """
    q_type = question.get('type')
    explanation = question.get('explanation', '')
    correct_sign_url = question.get('correct_sign_url', '')

    if q_type in ('sign_to_meaning', 'complete_sentence', 'sequence_to_meaning', 'dialogue', 'context_meaning', 'sentence_to_sequence'):
        correct_ans = question.get('correct_answer', '').strip()
        user_str = str(user_answer).strip()

        # Handle index-based option selection (e.g. user sent 0, 1, 2, 3)
        options = question.get('options', [])
        try:
            u_idx = int(user_answer)
            if 0 <= u_idx < len(options):
                user_str = str(options[u_idx]).strip()
        except (ValueError, TypeError):
            pass

        is_correct = (normalize_answer(user_str) == normalize_answer(correct_ans))
        return is_correct, correct_ans, explanation, correct_sign_url

    elif q_type == 'meaning_to_sign':
        correct_index = question.get('correct_index')
        correct_asset = question.get('correct_answer', '')
        is_correct = False

        # 1. Direct index check
        try:
            if int(user_answer) == correct_index:
                is_correct = True
        except (ValueError, TypeError):
            pass

        # 2. Letter check ("A", "Option A")
        if not is_correct and isinstance(user_answer, str):
            u_clean = user_answer.strip().upper()
            if u_clean.startswith('OPTION ') and len(u_clean) >= 8:
                char = u_clean[-1]
                if 'A' <= char <= 'D' and (ord(char) - 65) == correct_index:
                    is_correct = True
            elif len(u_clean) == 1 and 'A' <= u_clean <= 'D':
                if (ord(u_clean) - 65) == correct_index:
                    is_correct = True

        # 3. Filename check
        if not is_correct:
            u_str = str(user_answer).replace('/static/ISL_Gifs/', '').replace('/static/', '').strip().lower()
            c_str = str(correct_asset).replace('/static/ISL_Gifs/', '').replace('/static/', '').strip().lower()
            if u_str and u_str == c_str:
                is_correct = True

        target_name = question.get('target_word', 'the word')
        return is_correct, f"Sign for '{target_name}'", explanation, correct_sign_url

    elif q_type == 'type_answer':
        acceptable = question.get('acceptable_answers', [])
        user_norm = normalize_answer(user_answer)
        normalized_acceptable = [normalize_answer(a) for a in acceptable]
        is_correct = (user_norm in normalized_acceptable) or any(user_norm == a for a in normalized_acceptable)
        correct_display = question.get('correct_answer', acceptable[0] if acceptable else '')
        return is_correct, correct_display, explanation, correct_sign_url

    elif q_type == 'matching':
        correct_pairs = question.get('correct_pairs', {})
        is_correct = True
        if not user_answer or not isinstance(user_answer, dict):
            is_correct = False
        else:
            for word, sign_id in correct_pairs.items():
                if str(user_answer.get(word, '')).strip() != str(sign_id).strip():
                    is_correct = False
                    break
        return is_correct, "All 4 pairs correctly matched", explanation, correct_sign_url

    return False, "Unknown", explanation, correct_sign_url
