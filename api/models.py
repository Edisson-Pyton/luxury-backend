from django.db import models
from django.contrib.auth.models import User


# ── Perfil del usuario ────────────────────────────────────────
class UserProfile(models.Model):
    user       = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone      = models.CharField(max_length=15, blank=True)
    age        = models.IntegerField(null=True, blank=True)
    weight     = models.FloatField(null=True, blank=True)
    height     = models.FloatField(null=True, blank=True)
    goal       = models.CharField(max_length=50, blank=True)
    form_completed = models.BooleanField(default=False)

    # Días de descanso (guardados como "0,6" = Lunes y Domingo)
    rest_days        = models.CharField(max_length=20, blank=True, default='')
    rest_days_set_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'Perfil de {self.user.username}'


# ── Racha física ──────────────────────────────────────────────
class WorkoutStreak(models.Model):
    user            = models.OneToOneField(User, on_delete=models.CASCADE, related_name='workout_streak')
    streak          = models.IntegerField(default=0)
    last_workout_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f'Racha física de {self.user.username}: {self.streak} días'


# ── Racha mental ──────────────────────────────────────────────
class MentalStreak(models.Model):
    user             = models.OneToOneField(User, on_delete=models.CASCADE, related_name='mental_streak')
    streak           = models.IntegerField(default=0)
    last_mental_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f'Racha mental de {self.user.username}: {self.streak} días'


# ── Progreso de ejercicios por día ────────────────────────────
class WorkoutProgress(models.Model):
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='workout_progress')
    date       = models.DateField()
    goal       = models.CharField(max_length=50)
    exercise_index = models.IntegerField()

    class Meta:
        unique_together = ('user', 'date', 'goal', 'exercise_index')

    def __str__(self):
        return f'{self.user.username} - {self.date} - ejercicio {self.exercise_index}'


# ── Progreso de actividades mentales por día ──────────────────
class MentalProgress(models.Model):
    user           = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mental_progress')
    date           = models.DateField()
    activity_index = models.IntegerField()

    class Meta:
        unique_together = ('user', 'date', 'activity_index')

    def __str__(self):
        return f'{self.user.username} - {self.date} - actividad {self.activity_index}'


# ── Estado de ánimo ───────────────────────────────────────────
class MoodEntry(models.Model):
    user  = models.ForeignKey(User, on_delete=models.CASCADE, related_name='moods')
    date  = models.DateField()
    mood  = models.IntegerField()  # 1=Mal, 2=Regular, 3=Bien, 4=Excelente

    class Meta:
        unique_together = ('user', 'date')

    def __str__(self):
        return f'{self.user.username} - {self.date} - ánimo {self.mood}'


# ── Test psicológico ──────────────────────────────────────────
class MentalTest(models.Model):
    user    = models.OneToOneField(User, on_delete=models.CASCADE, related_name='mental_test')
    profile = models.CharField(max_length=50)
    score   = models.IntegerField()
    answers = models.CharField(max_length=200)  # guardado como "0,1,2,3,..."
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Test de {self.user.username}: {self.profile}'


