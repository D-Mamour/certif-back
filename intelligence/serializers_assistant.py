"""Sérialise et valide les échanges avec l'assistant Chantial."""
from rest_framework import serializers


class AssistantQuestionSerializer(serializers.Serializer):
    """Valide une question envoyée au chatbot et le projet ciblé."""

    question = serializers.CharField(min_length=2, max_length=1000, trim_whitespace=True)
    projet = serializers.UUIDField(required=False, allow_null=True)
