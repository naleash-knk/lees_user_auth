from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import generics
from django.contrib.auth import authenticate
from .serializers import LoginSerializer, UserSerializer
from rest_framework.decorators import api_view
from .models import CustomUser, ListeningSession
from rest_framework.permissions import IsAuthenticated
from openai import OpenAI
from google.cloud import texttospeech
from langdetect import detect
import os
import logging
from django.conf import settings
from phonemizer import phonemize
import soundfile as sf
import numpy as np
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
import json
import traceback
import librosa
import random
import google.cloud.texttospeech as tts
import nltk
from nltk.corpus import cmudict
from rest_framework.permissions import AllowAny



nltk.download('cmudict')

logger = logging.getLogger(__name__)

class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        username = serializer.validated_data['username']
        password = serializer.validated_data['password']
        user = authenticate(username=username, password=password)
        if user is not None:
            refresh = RefreshToken.for_user(user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            })
        return Response({'detail': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

class UserCreateView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_class=[AllowAny]

class OpenAITextView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key="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",
        )

        query = request.data.get("query")
        image_url = request.data.get("image_url")



        try:
            completion = client.chat.completions.create(
                extra_body={},
                model="google/gemini-2.0-pro-exp-02-05:free",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": query
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": image_url
                                }
                            }
                        ]
                    }
                ]
            )

            response_content = completion.choices[0].message.content
            
            return JsonResponse({"response": response_content})
        except Exception as e:
            logger.error(f"Error in OpenAITextView: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


PHONEME_TO_FRAME_RANGE = {
    "p": (1, 80), "b": (1, 80), "m": (1, 80),  
    "f": (81, 160), "v": (81, 160), "th": (81, 160), "dh": (81, 160),  
    "t": (81, 160), "d": (81, 160), "s": (81, 160), "z": (81, 160),  
    "k": (81, 160), "g": (81, 160), "ng": (81, 160),  
    "ch": (81, 160), "j": (81, 160), "sh": (81, 160), "zh": (81, 160),  
    "r": (81, 160), "l": (81, 160),  
    "aa": (161, 242), "ae": (161, 242), "ah": (161, 242), "ao": (161, 242),  
    "aw": (161, 242), "ay": (161, 242), "eh": (161, 242), "ey": (161, 242),  
    "ih": (161, 242), "iy": (161, 242), "ow": (161, 242), "oy": (161, 242),  
    "uh": (161, 242), "uw": (161, 242), "h": (161, 242), "w": (161, 242),  
    "y": (161, 242)  
}

from rest_framework.permissions import IsAuthenticated

class OpenAIAudioView(APIView):
    permission_classes=[IsAuthenticated]
    def post(self, request, *args, **kwargs):
        try:
            client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=os.getenv("OPENAI_API_KEY")
            )

            query = request.data.get("query", "") + " in 50 Words"
            print(f"Received Query: {query}")  

            completion = client.chat.completions.create(
                extra_body={},
                model="google/gemini-2.0-pro-exp-02-05:free",
                messages=[{"role": "user", "content": [{"type": "text", "text": query}]}],
            )

            response_content = completion.choices[0].message.content
            print(f"OpenAI Response: {response_content}")  

            cleaned_response = response_content.replace('*', '')

            detected_language = detect(query)
            print(f"Detected Language: {detected_language}")

            if detected_language == 'ta':
                language_code = "ta-IN"
                voice_name = "ta-IN-Standard-B"
            else:
                language_code = "en-US"
                voice_name = "en-US-Standard-J"
            
            tts_client = tts.TextToSpeechClient()
            input_text = tts.SynthesisInput(text=cleaned_response)
            audio_config = tts.AudioConfig(audio_encoding=tts.AudioEncoding.LINEAR16)
            voice = tts.VoiceSelectionParams(language_code=language_code, name=voice_name)

            tts_response = tts_client.synthesize_speech(input=input_text, voice=voice, audio_config=audio_config)
            print("Google TTS Synthesis Completed")  

            media_path = settings.MEDIA_ROOT
            os.makedirs(media_path, exist_ok=True)
            audio_path = os.path.join(media_path, "response_audio.wav")

            with open(audio_path, "wb") as out:
                out.write(tts_response.audio_content)

            print(f"Audio File Saved: {audio_path}")

            def text_to_phonemes(text):
                words = text.lower().split()
                pronouncing_dict = cmudict.dict()
                phonemes = [pronouncing_dict[word][0] if word in pronouncing_dict else ["?"] for word in words]
                return [phoneme for sublist in phonemes for phoneme in sublist]  

            phoneme_list = text_to_phonemes(cleaned_response)
            print(f"Phonemes: {phoneme_list}")  

            audio_data, samplerate = sf.read(audio_path)
            duration = len(audio_data) / samplerate
            print(f"Audio Duration: {duration} seconds")  

            avg_phoneme_duration = duration / max(len(phoneme_list), 1)

            visemes = []
            time_accumulator = 0
            for phoneme in phoneme_list:
                frame_range = PHONEME_TO_FRAME_RANGE.get(phoneme, (1, 80))  
                viseme_frame = random.randint(frame_range[0], frame_range[1])  
                visemes.append({"start": round(time_accumulator, 3), "viseme": viseme_frame})
                time_accumulator += avg_phoneme_duration

            print(f"Generated Visemes: {visemes}")  

            audio_url = request.build_absolute_uri(settings.MEDIA_URL + "response_audio.wav")
            print(f"Returning Audio URL: {audio_url}")  

            return JsonResponse({"audio_url": audio_url, "visemes": visemes})

        except Exception as e:
            error_trace = traceback.format_exc()
            print(f"Internal Server Error:\n{error_trace}")  
            return Response({"error": str(e), "traceback": error_trace}, status=500)

@api_view(['POST'])
def create_session(request):
    user = request.user
    song_name = request.data.get('song_name')
    song_url = request.data.get('song_url')
    session = ListeningSession.objects.create(
        session_id=str(uuid.uuid4()),
        host=user,
        song_name=song_name,
        song_url=song_url
    )
    return Response({'session_id': session.session_id})

@api_view(['GET'])
def get_session_status(request, session_id):
    try:
        session = ListeningSession.objects.get(session_id=session_id)
        return Response({
            'song_url': session.song_url,
            'is_playing': session.is_playing,
            'current_time': session.current_time
        })
    except ListeningSession.DoesNotExist:
        return Response({'error': 'Session not found'}, status=404)