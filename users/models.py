from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db import models

class CustomUserManager(BaseUserManager):
    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError('The Username field must be set')
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        return self.create_user(username, password, **extra_fields)

class CustomUser(AbstractBaseUser):
    username = models.CharField(max_length=150, unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    objects = CustomUserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.username


class ListeningSession(models.Model):
    session_id = models.CharField(max_length=100, unique=True)
    host = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='hosted_sessions')
    song_name = models.CharField(max_length=255)
    song_url = models.URLField()
    is_playing = models.BooleanField(default=False)
    current_time = models.FloatField(default=0.0)  # Current time in seconds
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Session {self.session_id} by {self.host.username}"