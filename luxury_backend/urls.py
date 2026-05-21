from django.contrib import admin
from django.urls import path
from api import views
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('admin/', admin.site.urls),

    # Auth
    path('api/register/', views.register),
    path('api/login/',    views.login),
    path('api/token/refresh/', TokenRefreshView.as_view()),

    # Perfil
    path('api/profile/',   views.user_profile),
    path('api/rest-days/', views.save_rest_days),

    # Ejercicios
    path('api/workout/progress/', views.workout_progress),
    path('api/workout/streak/',   views.workout_streak),

    # Salud mental
    path('api/mental/progress/', views.mental_progress),
    path('api/mental/streak/',   views.mental_streak),
    path('api/mental/mood/',     views.mood),
    path('api/mental/test/',     views.mental_test),
]