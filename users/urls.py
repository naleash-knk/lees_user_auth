# filepath: /l:/WorkSpace/Projects/spl/lees_user_auth/users/urls.py

from django.urls import path, re_path
from .views import UserCreateView, LoginView, OpenAITextView, OpenAIAudioView, ListeningSession


urlpatterns = [
    path('create/', UserCreateView.as_view(), name='user-create'),
    path('login/', LoginView.as_view(), name='user-login'),
    path('leegpt/textchat/', OpenAITextView.as_view(), name='leegpt-text'),
    path('leegpt/audiochat/', OpenAIAudioView.as_view(), name='leegpt-audio'),
    path('leegpt/session/', ListeningSession, name='session')
]
