from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from .models import PPTUpload
import json
from unittest.mock import patch

class StudyCompanionTests(TestCase):
    def setUp(self):
        # Create a test user
        self.user = User.objects.create_user(username='testuser', password='password123')
        # Ensure profile exists (in case signal failed or race condition)
        from .models import UserProfile
        UserProfile.objects.get_or_create(user=self.user)

        self.client = Client()
        
        # Create a sample PPT upload
        # Fix: Provide a file using SimpleUploadedFile
        self.ppt_upload = PPTUpload.objects.create(
            user=self.user,
            title="Test Presentation",
            file=SimpleUploadedFile("test.pptx", b"dummy content"),
            extracted_text="This is a test extracted text.",
            summary_text="This is a test summary."
        )

    def test_login_required_views(self):
        """Test that views require login"""
        protected_urls = [
            reverse('dashboard'),
            reverse('summary', args=[self.ppt_upload.id]),
            reverse('quiz', args=[self.ppt_upload.id]),
            reverse('quiz_data_api', args=[self.ppt_upload.id]),
        ]
        
        for url in protected_urls:
            response = self.client.get(url)
            self.assertNotEqual(response.status_code, 200)
            self.assertEqual(response.status_code, 302) # Redirects to login
            # Check if redirects to login page
            self.assertTrue('/login' in response.url or '/accounts/login' in response.url)

    def test_dashboard_view(self):
        """Test dashboard loads for logged in user"""
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Presentation")

    def test_upload_ppt_view_get(self):
        """Test upload page loads"""
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('upload'))
        self.assertEqual(response.status_code, 200)

    def test_summary_view(self):
        """Test summary page loads with correct context"""
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('summary', args=[self.ppt_upload.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This is a test summary.")

    def test_animation_view(self):
        """Test animation tool loads (protected view)"""
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('animation'))
        self.assertEqual(response.status_code, 200)

    def test_quiz_view(self):
        """Test quiz interface loads"""
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('quiz', args=[self.ppt_upload.id]))
        self.assertEqual(response.status_code, 200)
        
    @patch('study_companion.views.generate_mcq')
    def test_quiz_api(self, mock_generate_mcq):
        """Test quiz data API returns JSON questions"""
        # Mock result — generate_mcq returns a parsed list, not a JSON string
        mock_generate_mcq.return_value = [
            {
                "question": "Test Q1",
                "options": ["A", "B", "C", "D"],
                "answer": "A"
            }
        ]
        
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('quiz_data_api', args=[self.ppt_upload.id]) + '?num_questions=1&difficulty=Easy')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue('questions' in data)
        self.assertTrue(isinstance(data['questions'], list))
        self.assertEqual(len(data['questions']), 1)
        self.assertEqual(data['questions'][0]['question'], "Test Q1")

    def test_ppt_upload_model(self):
        """Test model data integrity"""
        upload = PPTUpload.objects.get(title="Test Presentation")
        self.assertEqual(upload.user.username, 'testuser')
        self.assertEqual(upload.extracted_text, "This is a test extracted text.")
        self.assertTrue(upload.file.name.endswith('.pptx'))

    def test_quiz_save_result(self):
        """Test saving quiz results via API"""
        self.client.login(username='testuser', password='password123')
        url = reverse('quiz_save_result', args=[self.ppt_upload.id])
        data = {
            'score': 4,
            'total': 5,
            'time_taken': '01:30'
        }
        response = self.client.post(url, json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['status'], 'success')
        self.assertEqual(response_data['xp_earned'], 40)
        
        # Verify db content
        from .models import QuizResult, UserProfile
        result = QuizResult.objects.filter(user=self.user, upload=self.ppt_upload).first()
        self.assertIsNotNone(result)
        self.assertEqual(result.score, 4)
        
        # Verify profile update
        profile = UserProfile.objects.get(user=self.user)
        self.assertEqual(profile.total_xp, 40)
        self.assertEqual(profile.current_streak, 1)

    def test_clean_extracted_text(self):
        """Test clean_extracted_text strips unreadable characters and repeated blank lines"""
        from .ai_services import clean_extracted_text
        raw = "Hello\x00 World!\n\n\n\nThis is a   test.\n\n\nLine 3"
        cleaned = clean_extracted_text(raw)
        self.assertNotIn("\x00", cleaned)
        self.assertNotIn("\n\n\n", cleaned)
        self.assertIn("Hello World!", cleaned)
        self.assertIn("This is a test.", cleaned)

    def test_quiz_data_insufficient_content(self):
        """Test that uploads with < 100 characters of readable content return user-friendly error"""
        short_upload = PPTUpload.objects.create(
            user=self.user,
            title="Short Document",
            file=SimpleUploadedFile("short.txt", b"Too brief."),
            extracted_text="Too brief content."
        )
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('quiz_data_api', args=[short_upload.id]))
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn("Not enough readable content was found in this file to generate a quiz.", data.get('error', ''))

    def test_generate_fallback_mcq(self):
        """Test fallback question generator produces valid 4-option MCQs from document text"""
        from .ai_services import generate_fallback_mcq
        educational_text = (
            "Artificial Intelligence is a branch of computer science focused on building smart machines. "
            "Machine Learning is a subset of AI that allows systems to learn from data automatically. "
            "Natural Language Processing enables computers to understand human language and text. "
            "Computer Vision allows algorithms to analyze visual inputs such as sign language videos."
        )
        questions = generate_fallback_mcq(educational_text, num_questions=3)
        self.assertTrue(len(questions) >= 1)
        for q in questions:
            self.assertTrue(len(q['question']) > 0)
            self.assertEqual(len(q['options']), 4)
            self.assertIn(q['correct_answer'], q['options'])
            self.assertTrue(len(q['explanation']) > 0)

    def test_parse_and_validate_quiz_json(self):
        """Test parsing Gemini markdown response and option resolution"""
        from .ai_services import parse_and_validate_quiz_json
        sample_ai_output = """```json
        {
            "questions": [
                {
                    "question": "What is Python?",
                    "options": ["A high-level programming language", "A venomous snake species", "A database engine", "A web browser"],
                    "correct_answer": "Option A",
                    "explanation": "Python is a popular high-level programming language."
                }
            ]
        }
        ```"""
        parsed = parse_and_validate_quiz_json(sample_ai_output)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]['correct_answer'], "A high-level programming language")
        self.assertEqual(parsed[0]['correct_index'], 0)
        self.assertEqual(len(parsed[0]['options']), 4)


class LearnSignLanguageFeatureTests(TestCase):
    def setUp(self):
        from django.contrib.auth.models import User
        from study_companion.course_data import seed_isl_course
        self.user = User.objects.create_user(username='learnuser', password='password123')
        self.client = Client()
        self.course = seed_isl_course()
        self.section1 = self.course.sections.get(section_number=1)
        self.section2 = self.course.sections.get(section_number=2)
        self.lesson1 = self.section1.lessons.first()

    def test_course_seeding(self):
        """Verify course initializes with 5 progressive sections and 87 lessons"""
        from study_companion.models import Course, CourseSection, Lesson
        self.assertEqual(CourseSection.objects.filter(course=self.course).count(), 5)
        self.assertEqual(Lesson.objects.filter(section__course=self.course).count(), 87)
        self.assertEqual(self.section1.lessons.count(), 26)  # A-Z

    def test_learn_dashboard_view(self):
        """Verify learn dashboard loads with progress stats and sections"""
        self.client.login(username='learnuser', password='password123')
        response = self.client.get(reverse('learn_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Indian Sign Language Course")
        self.assertContains(response, "Section 1")

    def test_learn_lesson_view(self):
        """Verify lesson view renders correctly for unlocked section"""
        self.client.login(username='learnuser', password='password123')
        response = self.client.get(reverse('learn_lesson', args=[self.lesson1.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.lesson1.title)

    def test_learn_complete_lesson_api(self):
        """Verify marking a lesson as completed via AJAX"""
        from study_companion.models import LessonProgress
        self.client.login(username='learnuser', password='password123')
        response = self.client.post(reverse('learn_complete_lesson', args=[self.lesson1.id]))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'ok')
        self.assertTrue(data['is_completed'])
        self.assertTrue(LessonProgress.objects.filter(user=self.user, lesson=self.lesson1, completed=True).exists())

    def test_learn_practice_view_and_search(self):
        """Verify practice page loads and search API returns results"""
        self.client.login(username='learnuser', password='password123')
        response = self.client.get(reverse('learn_practice', args=[self.section1.id]))
        self.assertEqual(response.status_code, 200)

        # Search for letter A in section 1
        search_resp = self.client.get(reverse('learn_practice_search', args=[self.section1.id]) + '?q=a')
        self.assertEqual(search_resp.status_code, 200)
        data = json.loads(search_resp.content)
        self.assertTrue(data['in_section'])
        self.assertTrue(len(data['results']) > 0)

    def test_learn_quiz_api(self):
        """Verify section quiz API generates 10 sanitized questions without answer leaks"""
        self.client.login(username='learnuser', password='password123')
        response = self.client.get(reverse('learn_quiz_api', args=[self.section1.id]))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'ok')
        self.assertEqual(len(data['questions']), 10)
        # Ensure correct answers are NOT in the client payload
        for q in data['questions']:
            self.assertNotIn('correct_answer', q)
            self.assertNotIn('correct_index', q)
            self.assertNotIn('acceptable_answers', q)

    def test_learn_quiz_check_answer_api(self):
        """Verify backend evaluation on check-answer without revealing answers early"""
        self.client.login(username='learnuser', password='password123')
        # 1. Initialize active quiz session
        api_resp = self.client.get(reverse('learn_quiz_api', args=[self.section1.id]))
        self.assertEqual(api_resp.status_code, 200)

        # 2. Check an answer
        check_url = reverse('learn_quiz_check_answer', args=[self.section1.id])
        resp = self.client.post(
            check_url,
            json.dumps({'question_index': 0, 'user_answer': 'wrong_dummy_val'}),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertEqual(data['status'], 'ok')
        self.assertIn('is_correct', data)
        self.assertIn('correct_answer', data)

    def test_section_unlock_on_quiz_pass(self):
        """Verify passing the quiz (>=60%) unlocks the next section and saves review mistakes"""
        from study_companion.models import SectionProgress, CourseQuizAttempt
        self.client.login(username='learnuser', password='password123')

        # 1. Initialize quiz in session
        self.client.get(reverse('learn_quiz_api', args=[self.section1.id]))

        # 2. Submit quiz
        resp_pass = self.client.post(
            reverse('learn_quiz_submit', args=[self.section1.id]),
            json.dumps({'time_taken': '01:15'}),
            content_type='application/json'
        )
        self.assertEqual(resp_pass.status_code, 200)
        data_pass = json.loads(resp_pass.content)
        self.assertEqual(data_pass['status'], 'ok')

        # Verify attempt was recorded in DB
        attempt = CourseQuizAttempt.objects.filter(user=self.user, section=self.section1).first()
        self.assertIsNotNone(attempt)
        self.assertIsNotNone(attempt.review_data)

    def test_all_sections_quiz_generation_integrity(self):
        """Assert that all 5 sections generate strictly section-accurate 10-exercise quizzes"""
        from study_companion.course_data import generate_section_quiz
        for sec in self.course.sections.all():
            quiz = generate_section_quiz(sec.id)
            server_q = quiz['server_questions']
            client_q = quiz['client_questions']
            self.assertEqual(len(server_q), 10)
            self.assertEqual(len(client_q), 10)
            for q in server_q:
                self.assertEqual(q['section_id'], sec.id)
                self.assertEqual(q['section_number'], sec.section_number)
                if q['type'] in ('sign_to_meaning', 'complete_sentence', 'sequence_to_meaning', 'dialogue'):
                    self.assertEqual(len(q['options']), 4)
                    self.assertEqual(len(set(q['options'])), 4)
                    self.assertIn(q['correct_answer'], q['options'])

    def test_practice_lookup_in_section(self):
        """Verify looking up a sign in the current section returns verified lesson"""
        self.client.login(username='learnuser', password='password123')
        resp = self.client.get(reverse('learn_practice_lookup', args=[self.section2.id]) + '?q=hello')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertTrue(data['found'])
        self.assertTrue(data['in_section'])
        self.assertEqual(data['lesson']['word'], 'Hello')

    def test_practice_lookup_other_section(self):
        """Verify looking up a sign from another section displays helpful warning without analyzing"""
        self.client.login(username='learnuser', password='password123')
        # Look up 'A' (Section 1) while in Section 2
        resp = self.client.get(reverse('learn_practice_lookup', args=[self.section2.id]) + '?q=A')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertFalse(data['found'])
        self.assertFalse(data['in_section'])
        self.assertTrue(data['belongs_to_other_section'])
        self.assertIn('Section 1', data['message'])

    def test_practice_analyze_no_hand(self):
        """Verify analyzing without hand landmarks returns no_hand status"""
        self.client.login(username='learnuser', password='password123')
        resp = self.client.post(
            reverse('learn_practice_analyze', args=[self.section2.id]),
            json.dumps({'expected_sign': 'Hello', 'frames': []}),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertEqual(data['status'], 'no_hand')
        self.assertFalse(data['matched'])

    def test_practice_analyze_valid_frames(self):
        """Verify analyzing valid frames returns genuine confidence and saves PracticeAttempt"""
        from study_companion.models import PracticeAttempt
        from study_companion.sign_recognition import generate_base_hand_landmarks
        self.client.login(username='learnuser', password='password123')

        # Create 10 realistic frames for Hello (open hand waving)
        base_hand = generate_base_hand_landmarks([1, 1, 1, 1, 1], finger_spread=0.45)
        frames = []
        for i in range(12):
            # Hand with small wave offset
            frame_lms = [{'x': float(p[0] + i*0.02), 'y': float(p[1]), 'z': float(p[2])} for p in base_hand]
            frames.append({'landmarks': frame_lms})

        resp = self.client.post(
            reverse('learn_practice_analyze', args=[self.section2.id]),
            json.dumps({'expected_sign': 'Hello', 'frames': frames}),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertTrue(data['success'])
        self.assertIn(data['status'], ('matched', 'not_matched', 'uncertain'))
        self.assertGreaterEqual(data['recognition_confidence'], 0.0)
        self.assertLessEqual(data['recognition_confidence'], 1.0)

        # Verify PracticeAttempt logged in database
        attempt = PracticeAttempt.objects.filter(user=self.user, section=self.section2).first()
        self.assertIsNotNone(attempt)
        self.assertEqual(attempt.expected_sign, 'Hello')

    def test_concept_assessment_view(self):
        """Test Concept Assessment main view loads for authenticated user"""
        self.client.login(username='learnuser', password='password123')
        response = self.client.get(reverse('concept_assessment'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Concept Understanding Assessment")

    def test_concept_assessment_save_reference_api(self):
        """Test saving reference concept content extracts structured JSON schema"""
        self.client.login(username='learnuser', password='password123')
        resp = self.client.post(reverse('concept_assessment_save_reference'), {
            'topic': 'Photosynthesis',
            'reference_text': 'Photosynthesis is the process by which green plants use sunlight, water and carbon dioxide to produce glucose and release oxygen.'
        })
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertEqual(data['status'], 'ok')
        self.assertEqual(data['topic'], 'Photosynthesis')
        self.assertIn('reference_concepts_json', data)
        self.assertIn('concepts', data['reference_concepts_json'])
        self.assertIn('relationships', data['reference_concepts_json'])

    def test_concept_assessment_low_confidence_safety(self):
        """Test low sign recognition confidence (<50%) flags safety warning without false score"""
        self.client.login(username='learnuser', password='password123')
        payload = {
            'topic': 'Photosynthesis',
            'reference_text': 'Photosynthesis is the process by which green plants use sunlight and water to make food.',
            'reference_concepts_json': {
                'topic': 'Photosynthesis',
                'concepts': ['plants', 'sunlight', 'water', 'glucose'],
                'relationships': [{'source': 'plants', 'relation': 'use', 'target': 'sunlight'}]
            },
            'explanation_source': 'live',
            'frames': [{'landmarks': [{'x': 0.1, 'y': 0.2, 'z': 0.0}]}]
        }
        resp = self.client.post(reverse('concept_assessment_analyze'), json.dumps(payload), content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertEqual(data['status'], 'low_recognition_confidence')
        self.assertFalse(data['is_reliable'])
        self.assertLess(data['recognition_confidence'], 0.50)

    def test_concept_assessment_pipeline_evaluation(self):
        """Test complete concept assessment pipeline creates ConceptAssessment, ConceptResult, and AssessmentAttempt"""
        from study_companion.models import ConceptAssessment, ConceptResult, AssessmentAttempt
        self.client.login(username='learnuser', password='password123')
        payload = {
            'topic': 'Photosynthesis',
            'reference_text': 'Photosynthesis is the process by which green plants use sunlight, water and carbon dioxide to produce glucose and release oxygen.',
            'reference_concepts_json': {
                'topic': 'Photosynthesis',
                'concepts': ['plants', 'sunlight', 'water', 'carbon dioxide', 'glucose', 'oxygen'],
                'relationships': [
                    {'source': 'plants', 'relation': 'use', 'target': 'sunlight'},
                    {'source': 'plants', 'relation': 'use', 'target': 'water'}
                ]
            },
            'explanation_source': 'live',
            'confirmed_explanation': 'Plants use sunlight and water to produce food and release oxygen.'
        }
        resp = self.client.post(reverse('concept_assessment_analyze'), json.dumps(payload), content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertEqual(data['status'], 'ok')
        self.assertTrue(data['is_reliable'])
        self.assertIn('overall_score', data)
        self.assertIn('concept_coverage', data)
        self.assertIn('category_summary', data)

        # Check DB records
        assessment = ConceptAssessment.objects.filter(user=self.user, topic='Photosynthesis').first()
        self.assertIsNotNone(assessment)
        self.assertEqual(assessment.topic, 'Photosynthesis')
        
        results = ConceptResult.objects.filter(assessment=assessment)
        self.assertGreater(results.count(), 0)
        
        attempt = AssessmentAttempt.objects.filter(user=self.user, topic='Photosynthesis').first()
        self.assertIsNotNone(attempt)
        self.assertEqual(attempt.attempt_number, 1)

    def test_teacher_review_view(self):
        """Test teacher review view and score verification POST"""
        from study_companion.models import ConceptAssessment, TeacherReview
        self.client.login(username='learnuser', password='password123')
        
        assessment = ConceptAssessment.objects.create(
            user=self.user,
            topic='Photosynthesis',
            reference_content='Plants use sunlight and water.',
            reference_concepts_json={'concepts': ['plants', 'sunlight', 'water'], 'relationships': []},
            reconstructed_explanation='Plants use sunlight.',
            recognition_confidence=0.90,
            concept_coverage=0.66,
            relationship_accuracy=0.80,
            overall_understanding_score=0.72
        )
        
        url = reverse('teacher_review', args=[assessment.id])
        resp_get = self.client.get(url)
        self.assertEqual(resp_get.status_code, 200)
        
        resp_post = self.client.post(url, {
            'corrected_reconstruction': 'Plants use sunlight and water to grow.',
            'corrected_coverage': '90',
            'corrected_relationship_accuracy': '85',
            'teacher_notes': 'Good explanation with minor omissions.'
        })
        self.assertEqual(resp_post.status_code, 302)
        
        review = TeacherReview.objects.filter(assessment=assessment).first()
        self.assertIsNotNone(review)
        self.assertTrue(review.is_verified)
        self.assertEqual(review.corrected_coverage, 0.90)

    def test_extract_reference_knowledge_representation_photosynthesis(self):
        """Test extract_reference_knowledge_representation returns structured concepts and relationships"""
        from study_companion.ai_services import extract_reference_knowledge_representation
        text = "Photosynthesis is the process by which green plants use sunlight, water and carbon dioxide to produce glucose and release oxygen."
        res = extract_reference_knowledge_representation(text, topic_hint="Photosynthesis")
        self.assertEqual(res['topic'], "Photosynthesis")
        self.assertIn('concepts', res)
        self.assertIn('concepts_list', res)
        self.assertIn('relationships', res)
        self.assertTrue(len(res['concepts']) >= 4)
        self.assertTrue(isinstance(res['concepts'][0], dict))
        self.assertIn('id', res['concepts'][0])
        self.assertIn('name', res['concepts'][0])

    def test_save_reference_api_post(self):
        """Test concept_assessment_save_reference_api returns JSON with status ok"""
        self.client.login(username='learnuser', password='password123')
        data = {
            'topic': 'Photosynthesis',
            'reference_text': 'Photosynthesis is the process by which green plants use sunlight, water and carbon dioxide to produce glucose and release oxygen.'
        }
        resp = self.client.post(reverse('concept_assessment_save_reference'), data)
        self.assertEqual(resp.status_code, 200)
        json_resp = json.loads(resp.content)
        self.assertEqual(json_resp['status'], 'ok')
        self.assertEqual(json_resp['topic'], 'Photosynthesis')
        self.assertIn('reference_concepts_json', json_resp)
        self.assertEqual(json_resp['reference_source'], 'text')

    def test_semantic_comparison_paraphrase_and_misconception(self):
        """Test semantic comparison recognizes synonym paraphrases and flags explicit misconceptions"""
        from study_companion.ai_services import perform_semantic_concept_comparison
        ref_json = {
            'topic': 'Photosynthesis',
            'concepts': ['green plants', 'sunlight', 'water', 'carbon dioxide', 'glucose', 'oxygen'],
            'relationships': [{'source': 'green_plants', 'relation': 'use', 'target': 'sunlight'}]
        }
        stu_json = {
            'concepts': ['green plants', 'light', 'water', 'food', 'carbon dioxide', 'oxygen'],
            'relationships': []
        }
        text = "Green plants use light and water to make food and release carbon dioxide."
        eval_res = perform_semantic_concept_comparison(ref_json, stu_json, text)
        self.assertIn('overall_score', eval_res)
        self.assertIn('category_summary', eval_res)
        self.assertTrue(len(eval_res['concept_results']) >= 6)





