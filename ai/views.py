import structlog
from rest_framework.decorators import api_view, permission_classes, throttle_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from drf_spectacular.utils import extend_schema

from .serializers import (
    ConversationSerializer, MessageSerializer, 
    AudioTranscribeSerializer, ImageUploadSerializer
)
from .services import AIService
from openai import OpenAI
from django.conf import settings
import os
import tempfile

logger = structlog.get_logger(__name__)

class StandardPagination(PageNumberPagination):
    page_size = 20
    max_page_size = 100

@extend_schema(
    responses={200: ConversationSerializer(many=True)},
    summary="Get Conversations"
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([ScopedRateThrottle])
def get_conversations(request):
    """Fetch user's chat history list."""
    conversations = AIService.get_user_conversations(request.user)
    paginator = StandardPagination()
    page = paginator.paginate_queryset(conversations, request)
    serializer = ConversationSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)

get_conversations.throttle_scope = 'conversation'

@extend_schema(
    responses={200: MessageSerializer(many=True)},
    summary="Get Chat Messages"
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([ScopedRateThrottle])
def get_messages(request, conversation_id):
    """Fetch messages inside a chat."""
    try:
        messages = AIService.get_messages(request.user, conversation_id)
        paginator = StandardPagination()
        page = paginator.paginate_queryset(messages, request)
        serializer = MessageSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)
    except Exception as e:
        logger.error("fetch_messages_error", error=str(e))
        return Response({"detail": "Conversation not found"}, status=404)

get_messages.throttle_scope = 'conversation'

@extend_schema(
    responses={200: dict},
    summary="Delete Conversation"
)
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
@throttle_classes([ScopedRateThrottle])
def delete_conversation(request, conversation_id):
    """Delete a chat session."""
    try:
        AIService.delete_conversation(request.user, conversation_id)
        return Response({"message": "Conversation deleted."})
    except Exception:
        return Response({"detail": "Conversation not found"}, status=404)

delete_conversation.throttle_scope = 'conversation'

@extend_schema(
    request=AudioTranscribeSerializer,
    responses={200: dict},
    summary="Transcribe Audio"
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([ScopedRateThrottle])
@parser_classes([MultiPartParser, FormParser])
def transcribe_audio(request):
    """Transcribe audio file using Whisper."""
    serializer = AudioTranscribeSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    audio_file = serializer.validated_data['audio']
    
    try:
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        filename = audio_file.name if hasattr(audio_file, 'name') and audio_file.name else 'audio.webm'
        if '.' not in filename or filename.split('.')[-1].lower() not in['mp3', 'wav', 'm4a', 'webm', 'aac', 'ogg', 'flac', 'mp4']:
            filename = 'audio.webm'
            
        file_tuple = (filename, audio_file.read())
            
        transcript = client.audio.transcriptions.create(
            model="whisper-1", 
            file=file_tuple
        )
        return Response({"text": transcript.text})

    except Exception as e:
        logger.error("transcription_failed", error=str(e))
        return Response({"detail": "Transcription failed."}, status=500)

transcribe_audio.throttle_scope = 'media'

@extend_schema(
    request=ImageUploadSerializer,
    responses={200: dict},
    summary="Upload Chat Image"
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([ScopedRateThrottle])
@parser_classes([MultiPartParser, FormParser])
def upload_chat_image(request):
    """Upload an image to a chat."""
    serializer = ImageUploadSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)
    
    conversation_id = request.data.get('conversation_id')
    if not conversation_id:
        return Response({"detail": "Conversation ID required"}, status=400)

    try:
        from .models import Conversation, Message
        conv = Conversation.objects.get(id=conversation_id, user=request.user, is_active=True)
        message = Message.objects.create(
            conversation=conv,
            sender='user',
            text='',
            image=serializer.validated_data['image']
        )
        
        url = message.image.url
        if not url.startswith('http'):
            url = request.build_absolute_uri(url)
            
        return Response({
            "message": "Image uploaded", 
            "image_id": message.id, 
            "url": url
        })
    except Conversation.DoesNotExist:
        return Response({"detail": "Conversation not found"}, status=404)

upload_chat_image.throttle_scope = 'media'