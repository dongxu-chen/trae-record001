from rest_framework import serializers
from django.db.models import Count
from django.contrib.auth.models import User
from .models import Question, Choice, Vote


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username']


class ChoiceSerializer(serializers.ModelSerializer):
    vote_count = serializers.SerializerMethodField()
    percentage = serializers.SerializerMethodField()
    is_custom = serializers.BooleanField(read_only=True)
    created_by = UserSerializer(read_only=True)

    class Meta:
        model = Choice
        fields = ['id', 'text', 'vote_count', 'percentage', 'is_custom', 'created_by']

    def _get_vote_count(self, obj):
        return getattr(obj, '_vote_count', None) or obj.votes.count()

    def get_vote_count(self, obj):
        return self._get_vote_count(obj)

    def get_percentage(self, obj):
        question = obj.question
        total = getattr(question, '_total_votes', None)
        if total is None:
            total = Vote.objects.filter(choice__question=question).count()
        if total == 0:
            return 0
        vote_count = self._get_vote_count(obj)
        return round((vote_count / total) * 100, 2)


class ChoiceWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ['id', 'text']


class CustomChoiceCreateSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    text = serializers.CharField(max_length=200, min_length=1)

    def validate(self, data):
        question_id = data.get('question_id')
        text = data.get('text').strip()

        try:
            question = Question.objects.get(id=question_id)
        except Question.DoesNotExist:
            raise serializers.ValidationError("问题不存在")

        if not question.allow_custom_choices:
            raise serializers.ValidationError("该问题不允许自定义选项")

        if not question.is_active:
            raise serializers.ValidationError("该问题已关闭")

        existing = Choice.objects.filter(question=question, text__iexact=text)
        if existing.exists():
            raise serializers.ValidationError("该选项已存在")

        existing_count = Choice.objects.filter(question=question).count()
        if existing_count >= 20:
            raise serializers.ValidationError("该问题选项数量已达上限")

        return data


class QuestionListSerializer(serializers.ModelSerializer):
    total_votes = serializers.SerializerMethodField()
    choice_count = serializers.SerializerMethodField()
    created_by = UserSerializer(read_only=True)
    allow_custom_choices = serializers.BooleanField(read_only=True)

    class Meta:
        model = Question
        fields = ['id', 'title', 'description', 'created_at', 'is_active', 
                  'allow_multiple', 'allow_custom_choices', 'created_by',
                  'total_votes', 'choice_count']

    def get_total_votes(self, obj):
        total = getattr(obj, '_total_votes', None)
        if total is None:
            total = Vote.objects.filter(choice__question=obj).count()
        return total

    def get_choice_count(self, obj):
        count = getattr(obj, '_choice_count', None)
        if count is None:
            count = obj.choices.count()
        return count


class QuestionDetailSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True, read_only=True)
    total_votes = serializers.SerializerMethodField()
    created_by = UserSerializer(read_only=True)
    allow_custom_choices = serializers.BooleanField(read_only=True)

    class Meta:
        model = Question
        fields = ['id', 'title', 'description', 'created_at', 'is_active', 
                  'allow_multiple', 'allow_custom_choices', 'created_by',
                  'total_votes', 'choices']

    def get_total_votes(self, obj):
        total = getattr(obj, '_total_votes', None)
        if total is None:
            total = Vote.objects.filter(choice__question=obj).count()
        return total


class QuestionCreateSerializer(serializers.ModelSerializer):
    choices = ChoiceWriteSerializer(many=True)

    class Meta:
        model = Question
        fields = ['title', 'description', 'allow_multiple', 'allow_custom_choices', 'choices']

    def validate_choices(self, value):
        if not value or len(value) < 2:
            raise serializers.ValidationError("每个问题至少需要 2 个选项")
        if len(value) > 10:
            raise serializers.ValidationError("每个问题最多支持 10 个选项")
        return value

    def create(self, validated_data):
        choices_data = validated_data.pop('choices')
        user = self.context['request'].user
        if user.is_authenticated:
            validated_data['created_by'] = user
        question = Question.objects.create(**validated_data)
        for choice_data in choices_data:
            Choice.objects.create(question=question, **choice_data)
        return question


class VoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vote
        fields = ['id', 'choice', 'voted_at']


class VoteCreateSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    choice_ids = serializers.ListField(child=serializers.IntegerField(), required=False)
    custom_choice_text = serializers.CharField(max_length=200, required=False, allow_blank=True)

    def validate(self, data):
        from .models import Question, Choice

        question_id = data.get('question_id')
        choice_ids = data.get('choice_ids', [])
        custom_choice_text = data.get('custom_choice_text', '').strip()

        if not choice_ids and not custom_choice_text:
            raise serializers.ValidationError("请至少选择一个选项或添加自定义选项")

        try:
            question = Question.objects.get(id=question_id)
        except Question.DoesNotExist:
            raise serializers.ValidationError("问题不存在")

        if not question.is_active:
            raise serializers.ValidationError("该问题已关闭投票")

        all_choice_ids = list(choice_ids)
        new_choice = None

        if custom_choice_text:
            if not question.allow_custom_choices:
                raise serializers.ValidationError("该问题不允许自定义选项")

            existing = Choice.objects.filter(question=question, text__iexact=custom_choice_text).first()
            if existing:
                if existing.id not in all_choice_ids:
                    all_choice_ids.append(existing.id)
            else:
                existing_count = Choice.objects.filter(question=question).count()
                if existing_count >= 20:
                    raise serializers.ValidationError("该问题选项数量已达上限")
                new_choice = Choice.objects.create(
                    question=question,
                    text=custom_choice_text,
                    is_custom=True,
                    created_by=self.context['request'].user if self.context['request'].user.is_authenticated else None
                )
                all_choice_ids.append(new_choice.id)

        choices = Choice.objects.filter(id__in=all_choice_ids, question=question)
        if choices.count() != len(all_choice_ids):
            raise serializers.ValidationError("部分选项无效或不属于该问题")

        if not question.allow_multiple and len(all_choice_ids) > 1:
            raise serializers.ValidationError("该问题不允许多选")

        data['_final_choice_ids'] = all_choice_ids
        data['_new_choice'] = new_choice
        return data


class QuestionResultSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True, read_only=True)
    total_votes = serializers.SerializerMethodField()
    winner = serializers.SerializerMethodField()
    created_by = UserSerializer(read_only=True)
    allow_custom_choices = serializers.BooleanField(read_only=True)

    class Meta:
        model = Question
        fields = ['id', 'title', 'description', 'is_active', 'allow_multiple', 
                  'allow_custom_choices', 'created_by',
                  'total_votes', 'choices', 'winner']

    def get_total_votes(self, obj):
        total = getattr(obj, '_total_votes', None)
        if total is None:
            total = Vote.objects.filter(choice__question=obj).count()
        return total

    def get_winner(self, obj):
        choices = obj.choices.all() if hasattr(obj, 'choices') else []
        if not choices:
            return None

        max_votes = 0
        vote_counts = []
        for c in choices:
            cnt = getattr(c, '_vote_count', None)
            if cnt is None:
                cnt = c.votes.count()
            vote_counts.append((c.text, cnt))
            if cnt > max_votes:
                max_votes = cnt

        if max_votes == 0:
            return None

        winners = [text for text, cnt in vote_counts if cnt == max_votes]
        return winners
