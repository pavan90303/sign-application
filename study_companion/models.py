from django.db import models
from django.contrib.auth.models import User

class PPTUpload(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    file = models.FileField(upload_to='ppt_uploads/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    title = models.CharField(max_length=255, blank=True)
    
    # Store processed data to avoid re-running AI expensive calls
    extracted_text = models.TextField(blank=True, null=True)
    summary_text = models.TextField(blank=True, null=True)
    
    # Store generated quiz as JSON
    quiz_data = models.JSONField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.title} - {self.uploaded_at.strftime('%Y-%m-%d')}"

class QuizResult(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    upload = models.ForeignKey(PPTUpload, on_delete=models.CASCADE)
    score = models.IntegerField()
    total = models.IntegerField()
    time_taken = models.CharField(max_length=10)  # "MM:SS"
    completed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.upload.title} - {self.score}/{self.total}"

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    current_streak = models.IntegerField(default=0)
    longest_streak = models.IntegerField(default=0)
    last_activity_date = models.DateField(null=True, blank=True)
    total_xp = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.user.username}'s Profile"

# Signal to create UserProfile when User is created
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    try:
        instance.userprofile.save()
    except:
        pass


# ==========================================
# LEARN SIGN LANGUAGE (COURSE & PROGRESSION)
# ==========================================

import os
from django.conf import settings

class Course(models.Model):
    title = models.CharField(max_length=200, default="Indian Sign Language")
    subtitle = models.CharField(max_length=300, default="Beginner to Advanced")
    description = models.TextField(blank=True, default="Master Indian Sign Language from letters and basic vocabulary to full everyday conversations.")
    slug = models.SlugField(unique=True, default="isl-course")

    def __str__(self):
        return self.title


class CourseSection(models.Model):
    LEVEL_CHOICES = [
        ('Beginner', 'Beginner'),
        ('Intermediate', 'Intermediate'),
        ('Advanced', 'Advanced'),
    ]
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='sections')
    section_number = models.IntegerField()
    title = models.CharField(max_length=200)
    level = models.CharField(max_length=50, choices=LEVEL_CHOICES, default='Beginner')
    description = models.TextField(blank=True)
    order = models.IntegerField(default=1)

    class Meta:
        ordering = ['order', 'section_number']

    def __str__(self):
        return f"Section {self.section_number}: {self.title}"


class Lesson(models.Model):
    section = models.ForeignKey(CourseSection, on_delete=models.CASCADE, related_name='lessons')
    order = models.IntegerField(default=1)
    title = models.CharField(max_length=200)
    word_or_phrase = models.CharField(max_length=200)
    explanation = models.TextField(blank=True)
    sign_asset = models.CharField(max_length=255, blank=True)  # single filename or comma-separated sequence
    learning_type = models.CharField(max_length=50, default='word')  # letter, word, sentence, dialogue
    acceptable_answers = models.TextField(blank=True, default='')  # json or comma-separated acceptable variants

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.section.section_number}.{self.order} - {self.title}"

    @property
    def has_sign_asset(self):
        if not self.sign_asset:
            return False
        first_asset = self.sign_asset.split(',')[0].strip()
        asset_path = os.path.join(settings.BASE_DIR, 'assets', first_asset)
        return os.path.exists(asset_path)

    @property
    def sign_asset_list(self):
        if not self.sign_asset:
            return []
        items = []
        for s in self.sign_asset.split(','):
            cleaned = s.strip()
            if cleaned:
                asset_path = os.path.join(settings.BASE_DIR, 'assets', cleaned)
                items.append({
                    'name': os.path.splitext(cleaned)[0],
                    'filename': cleaned,
                    'exists': os.path.exists(asset_path),
                    'url': f"/static/{cleaned}"
                })
        return items

    def get_acceptable_answers(self):
        """Returns normalized list of acceptable string answers for typing exercises."""
        variants = {self.word_or_phrase.strip().lower()}
        if self.title:
            variants.add(self.title.strip().lower())
        if self.acceptable_answers:
            try:
                import json
                parsed = json.loads(self.acceptable_answers)
                if isinstance(parsed, list):
                    for p in parsed:
                        variants.add(str(p).strip().lower())
            except Exception:
                for p in self.acceptable_answers.split(','):
                    if p.strip():
                        variants.add(p.strip().lower())
        # Strip punctuation variants (e.g. "thank you" vs "thank you.")
        clean_variants = set()
        for v in variants:
            clean_variants.add(v)
            clean_variants.add(v.replace('.', '').replace('?', '').replace('!', '').strip())
            clean_variants.add(v.replace('-', ' ').strip())
            clean_variants.add(v.replace(' ', '').strip())
        return list(clean_variants)


class LessonProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lesson_progress')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='user_progress')
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'lesson')

    def __str__(self):
        return f"{self.user.username} - {self.lesson.title} - {'Done' if self.completed else 'Pending'}"


class SectionProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='section_progress')
    section = models.ForeignKey(CourseSection, on_delete=models.CASCADE, related_name='user_progress')
    unlocked = models.BooleanField(default=False)
    quiz_completed = models.BooleanField(default=False)
    best_score = models.IntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'section')

    def __str__(self):
        return f"{self.user.username} - {self.section.title} (Unlocked: {self.unlocked}, Quiz: {self.quiz_completed})"


class CourseQuizAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='course_quiz_attempts')
    section = models.ForeignKey(CourseSection, on_delete=models.CASCADE, related_name='quiz_attempts')
    score = models.IntegerField()  # percentage 0 - 100
    total_questions = models.IntegerField()
    correct_count = models.IntegerField(default=0)
    mistakes_count = models.IntegerField(default=0)
    passed = models.BooleanField(default=False)
    time_taken = models.CharField(max_length=20, default="00:00")
    review_data = models.TextField(blank=True, default='[]')  # JSON array of mistakes/review items
    completed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.section.title} Quiz: {self.score}% ({self.correct_count}/{self.total_questions}) ({'Passed' if self.passed else 'Failed'})"


class PracticeAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='practice_attempts')
    section = models.ForeignKey(CourseSection, on_delete=models.CASCADE, related_name='practice_attempts')
    lesson = models.ForeignKey(Lesson, on_delete=models.SET_NULL, null=True, blank=True, related_name='practice_attempts')
    expected_sign = models.CharField(max_length=100)
    predicted_sign = models.CharField(max_length=100, null=True, blank=True)
    recognition_confidence = models.FloatField(default=0.0)  # genuine 0.0 - 1.0 probability
    reference_similarity = models.FloatField(null=True, blank=True)  # if computed 0.0 - 1.0
    matched = models.BooleanField(default=False)
    status = models.CharField(max_length=50, default='uncertain')  # matched, not_matched, uncertain, no_hand, unsupported, insufficient_data
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.expected_sign} vs {self.predicted_sign} ({self.status}) [{self.recognition_confidence*100:.0f}%]"

