from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from datetime import date, timedelta
from .models import (
    UserProfile, WorkoutStreak, MentalStreak,
    WorkoutProgress, MentalProgress, MoodEntry, MentalTest
)


# ── Helper: obtener o crear objetos relacionados ──────────────
def get_or_create_profile(user):
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile

def get_or_create_workout_streak(user):
    streak, _ = WorkoutStreak.objects.get_or_create(user=user)
    return streak

def get_or_create_mental_streak(user):
    streak, _ = MentalStreak.objects.get_or_create(user=user)
    return streak


# ── Helper: verificar días de descanso ────────────────────────
def is_rest_day(profile):
    if not profile.rest_days:
        return False
    rest = [int(d) for d in profile.rest_days.split(',') if d]
    today_index = date.today().weekday()  # 0=Lun, 6=Dom
    return today_index in rest


# ── REGISTRO ──────────────────────────────────────────────────
@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    data = request.data
    name     = data.get('name', '').strip()
    email    = data.get('email', '').strip()
    phone    = data.get('phone', '').strip()
    password = data.get('password', '')

    if not all([name, email, password]):
        return Response(
            {'error': 'Nombre, correo y contraseña son obligatorios.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if User.objects.filter(email=email).exists():
        return Response(
            {'error': 'Ya existe una cuenta con ese correo.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Crea el usuario con contraseña encriptada automáticamente
    user = User.objects.create_user(
        username=email,
        email=email,
        password=password,
        first_name=name,
    )

    # Crea el perfil
    profile = get_or_create_profile(user)
    profile.phone = phone
    profile.save()

    # Genera tokens JWT
    refresh = RefreshToken.for_user(user)
    return Response({
        'access':  str(refresh.access_token),
        'refresh': str(refresh),
        'name':    user.first_name,
        'email':   user.email,
    }, status=status.HTTP_201_CREATED)


# ── LOGIN ─────────────────────────────────────────────────────
@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    email    = request.data.get('email', '').strip()
    password = request.data.get('password', '')

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response(
            {'error': 'No existe una cuenta con ese correo.'},
            status=status.HTTP_404_NOT_FOUND
        )

    if not user.check_password(password):
        return Response(
            {'error': 'Contraseña incorrecta.'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    refresh = RefreshToken.for_user(user)
    profile = get_or_create_profile(user)

    return Response({
        'access':         str(refresh.access_token),
        'refresh':        str(refresh),
        'name':           user.first_name,
        'email':          user.email,
        'form_completed': profile.form_completed,
    })


# ── PERFIL DEL USUARIO ────────────────────────────────────────
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    profile = get_or_create_profile(request.user)

    if request.method == 'GET':
        rest_days = [int(d) for d in profile.rest_days.split(',') if d] if profile.rest_days else []
        days_to_change = 0
        if profile.rest_days_set_date:
            diff = (timezone.now() - profile.rest_days_set_date).days
            days_to_change = max(0, 30 - diff)

        return Response({
            'name':           request.user.first_name,
            'email':          request.user.email,
            'phone':          profile.phone,
            'age':            profile.age,
            'weight':         profile.weight,
            'height':         profile.height,
            'goal':           profile.goal,
            'form_completed': profile.form_completed,
            'rest_days':      rest_days,
            'days_to_change': days_to_change,
        })

    if request.method == 'POST':
        data = request.data
        profile.age    = data.get('age', profile.age)
        profile.weight = data.get('weight', profile.weight)
        profile.height = data.get('height', profile.height)
        profile.goal   = data.get('goal', profile.goal)
        profile.form_completed = True
        profile.save()
        return Response({'message': 'Datos guardados correctamente.'})


# ── DÍAS DE DESCANSO ──────────────────────────────────────────
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_rest_days(request):
    profile   = get_or_create_profile(request.user)
    rest_days = request.data.get('rest_days', [])

    if len(rest_days) != 2:
        return Response(
            {'error': 'Debes elegir exactamente 2 días de descanso.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Verificar bloqueo de 30 días
    if profile.rest_days_set_date:
        diff = (timezone.now() - profile.rest_days_set_date).days
        if diff < 30:
            return Response(
                {'error': f'Puedes cambiar los días de descanso en {30 - diff} días.'},
                status=status.HTTP_400_BAD_REQUEST
            )

    profile.rest_days          = ','.join([str(d) for d in rest_days])
    profile.rest_days_set_date = timezone.now()
    profile.save()

    return Response({'message': 'Días de descanso guardados.'})


# ── PROGRESO DE EJERCICIOS ────────────────────────────────────
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def workout_progress(request):
    today = date.today()

    if request.method == 'GET':
        goal     = request.query_params.get('goal', '')
        progress = WorkoutProgress.objects.filter(
            user=request.user, date=today, goal=goal
        ).values_list('exercise_index', flat=True)
        return Response({'completed': list(progress)})

    if request.method == 'POST':
        index = request.data.get('index')
        goal  = request.data.get('goal', '')
        WorkoutProgress.objects.get_or_create(
            user=request.user, date=today,
            goal=goal, exercise_index=index
        )
        return Response({'message': 'Progreso guardado.'})


# ── RACHA FÍSICA ──────────────────────────────────────────────
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def workout_streak(request):
    streak  = get_or_create_workout_streak(request.user)
    profile = get_or_create_profile(request.user)
    today   = date.today()

    if request.method == 'GET':
        worked_today = streak.last_workout_date == today
        return Response({
            'streak':       streak.streak,
            'worked_today': worked_today,
            'is_rest_day':  is_rest_day(profile),
        })

    if request.method == 'POST':
        if streak.last_workout_date == today:
            return Response({'streak': streak.streak})

        rest_days = [int(d) for d in profile.rest_days.split(',') if d] if profile.rest_days else []

        if streak.last_workout_date:
            diff = (today - streak.last_workout_date).days
            if diff == 1:
                streak.streak += 1
            elif diff > 1:
                # Verifica si los días intermedios eran de descanso
                all_rest = all(
                    (streak.last_workout_date + timedelta(days=i)).weekday() in rest_days
                    for i in range(1, diff)
                )
                streak.streak = streak.streak + 1 if all_rest else 1
        else:
            streak.streak = 1

        streak.last_workout_date = today
        streak.save()
        return Response({'streak': streak.streak})


# ── RACHA MENTAL ──────────────────────────────────────────────
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def mental_streak(request):
    streak  = get_or_create_mental_streak(request.user)
    profile = get_or_create_profile(request.user)
    today   = date.today()

    if request.method == 'GET':
        done_today = streak.last_mental_date == today
        return Response({
            'streak':     streak.streak,
            'done_today': done_today,
            'is_rest_day': is_rest_day(profile),
        })

    if request.method == 'POST':
        if streak.last_mental_date == today:
            return Response({'streak': streak.streak})

        rest_days = [int(d) for d in profile.rest_days.split(',') if d] if profile.rest_days else []

        if streak.last_mental_date:
            diff = (today - streak.last_mental_date).days
            if diff == 1:
                streak.streak += 1
            elif diff > 1:
                all_rest = all(
                    (streak.last_mental_date + timedelta(days=i)).weekday() in rest_days
                    for i in range(1, diff)
                )
                streak.streak = streak.streak + 1 if all_rest else 1
        else:
            streak.streak = 1

        streak.last_mental_date = today
        streak.save()
        return Response({'streak': streak.streak})


# ── PROGRESO MENTAL ───────────────────────────────────────────
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def mental_progress(request):
    today = date.today()

    if request.method == 'GET':
        progress = MentalProgress.objects.filter(
            user=request.user, date=today
        ).values_list('activity_index', flat=True)
        return Response({'completed': list(progress)})

    if request.method == 'POST':
        index = request.data.get('index')
        MentalProgress.objects.get_or_create(
            user=request.user, date=today, activity_index=index
        )
        return Response({'message': 'Actividad guardada.'})


# ── ESTADO DE ÁNIMO ───────────────────────────────────────────
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def mood(request):
    today = date.today()

    if request.method == 'GET':
        # Últimos 7 días
        week_moods = {}
        for i in range(6, -1, -1):
            day = today - timedelta(days=i)
            entry = MoodEntry.objects.filter(
                user=request.user, date=day).first()
            if entry:
                key = day.strftime('%Y-%m-%d')
                week_moods[key] = entry.mood

        today_mood = MoodEntry.objects.filter(
            user=request.user, date=today).first()

        return Response({
            'today_mood': today_mood.mood if today_mood else None,
            'week_moods': week_moods,
        })

    if request.method == 'POST':
        mood_value = request.data.get('mood')
        # Solo 1 por día
        if MoodEntry.objects.filter(user=request.user, date=today).exists():
            return Response(
                {'error': 'Ya registraste tu estado de ánimo hoy.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        MoodEntry.objects.create(
            user=request.user, date=today, mood=mood_value)
        return Response({'message': 'Estado de ánimo guardado.'})


# ── TEST PSICOLÓGICO ──────────────────────────────────────────
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def mental_test(request):
    if request.method == 'GET':
        test = MentalTest.objects.filter(user=request.user).first()
        if not test:
            return Response({'done': False})
        return Response({
            'done':    True,
            'profile': test.profile,
            'score':   test.score,
            'answers': [int(a) for a in test.answers.split(',') if a],
        })

    if request.method == 'POST':
        profile_name = request.data.get('profile')
        score        = request.data.get('score')
        answers      = request.data.get('answers', [])

        MentalTest.objects.update_or_create(
            user=request.user,
            defaults={
                'profile': profile_name,
                'score':   score,
                'answers': ','.join([str(a) for a in answers]),
            }
        )
        return Response({'message': 'Test guardado.'})
