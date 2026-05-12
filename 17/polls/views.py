from rest_framework import status, permissions
from rest_framework.decorators import action, api_view, permission_classes, throttle_classes
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ViewSet
from rest_framework.generics import CreateAPIView
from django.db import transaction
from django.db.models import Count

from .models import Question, Choice, Vote
from .serializers import (
    QuestionListSerializer,
    QuestionDetailSerializer,
    QuestionCreateSerializer,
    QuestionResultSerializer,
    VoteCreateSerializer,
    VoteSerializer,
    CustomChoiceCreateSerializer,
)
from .permissions import (
    IsOwnerOrReadOnly,
    CanCreateQuestion,
)
from .throttling import (
    CreateQuestionThrottle,
    VoteThrottle,
    CustomChoiceThrottle,
)


class QuestionViewSet(ModelViewSet):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    throttle_classes = [CreateQuestionThrottle]

    def get_queryset(self):
        queryset = Question.objects.select_related('created_by')
        if self.action == 'list':
            return Question.annotate_with_counts(queryset)
        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return QuestionListSerializer
        elif self.action == 'create':
            return QuestionCreateSerializer
        elif self.action == 'results':
            return QuestionResultSerializer
        return QuestionDetailSerializer

    def get_object(self):
        obj = super().get_object()
        if self.action in ['results', 'retrieve']:
            annotated = Question.annotate_with_counts(
                Question.objects.select_related('created_by').filter(pk=obj.pk)
            )
            return annotated.first()
        return obj

    def get_throttles(self):
        if self.action == 'create':
            return [throttle() for throttle in [CreateQuestionThrottle]]
        return super().get_throttles()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        question = serializer.save()
        annotated = Question.annotate_with_counts(
            Question.objects.select_related('created_by').filter(pk=question.pk)
        )
        output_serializer = QuestionDetailSerializer(annotated.first())
        headers = self.get_success_headers(output_serializer.data)
        return Response(
            output_serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )

    @action(detail=True, methods=['get'])
    def results(self, request, pk=None):
        question = self.get_object()
        serializer = QuestionResultSerializer(question)
        return Response(serializer.data)


class CustomChoiceCreateView(CreateAPIView):
    serializer_class = CustomChoiceCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [CustomChoiceThrottle]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        question_id = serializer.validated_data['question_id']
        text = serializer.validated_data['text'].strip()

        with transaction.atomic():
            question = Question.objects.select_for_update().get(id=question_id)
            choice = Choice.objects.create(
                question=question,
                text=text,
                is_custom=True,
                created_by=request.user
            )

        return Response({
            'status': 'success',
            'choice_id': choice.id,
            'text': choice.text,
            'is_custom': True
        }, status=status.HTTP_201_CREATED)


class VoteViewSet(ViewSet):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [VoteThrottle]

    def create(self, request):
        serializer = VoteCreateSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)

        question_id = serializer.validated_data['question_id']
        choice_ids = serializer.validated_data.get('_final_choice_ids', [])
        new_choice = serializer.validated_data.get('_new_choice')

        voter_type, voter_id = Question.get_voter_identifier(request)
        voter_ip = self._get_client_ip(request)

        with transaction.atomic():
            question = Question.objects.select_for_update().get(id=question_id)
            choices = Choice.objects.select_for_update().filter(
                id__in=choice_ids,
                question=question
            )

            if voter_type == 'user':
                existing_votes = Vote.objects.filter(
                    choice__question=question,
                    voter_id=voter_id
                )
            else:
                existing_votes = Vote.objects.filter(
                    choice__question=question,
                    session_key=voter_id
                )

            if existing_votes.exists():
                existing_votes.delete()

            vote_list = []
            for choice in choices:
                vote_kwargs = {
                    'choice': choice,
                    'voter_ip': voter_ip,
                }
                if voter_type == 'user':
                    vote_kwargs['voter_id'] = voter_id
                else:
                    vote_kwargs['session_key'] = voter_id

                vote = Vote.objects.create(**vote_kwargs)
                vote_list.append(vote)

        result_serializer = VoteSerializer(vote_list, many=True)
        response_data = {
            'status': 'success',
            'votes': result_serializer.data,
        }
        if new_choice:
            response_data['new_choice_created'] = {
                'id': new_choice.id,
                'text': new_choice.text
            }

        return Response(
            response_data,
            status=status.HTTP_201_CREATED
        )

    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
