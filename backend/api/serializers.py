from typing import List, Dict, Optional
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from django.core.validators import (
    RegexValidator,
    MinLengthValidator,
    MaxLengthValidator,
)
from rest_framework.validators import UniqueValidator

import base64
import binascii
import re
import difflib
from django.core.files.base import ContentFile

from django.contrib.auth import authenticate, get_user_model
from .models import (
    Subscription,
    Ingredient,
    Recipe,
    RecipeIngredient,
    Favorite,
    ShoppingList,
)

from .constants import (
    MIN_COOKING_TIME,
    MAX_COOKING_TIME,
    MIN_VALUE,
    MAX_VALUE,
    MAX_LENGTH,
)


User = get_user_model()


class UserSerializer(serializers.ModelSerializer):

    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "is_subscribed",
            "avatar",
        ]

    def get_is_subscribed(self, obj):
        request = self.context.get("request")
        user = request.user
        if not user.is_authenticated:
            return False
        return user.subscriptions.filter(author=obj).exists()


class Base64ImageField(serializers.ImageField):
    """ "
    Пользовательское поле сериализатора для обработки изображений,
    закодированных в base64. Преобразует строку base64 в объект ContentFile,
    который может быть сохранен как изображение.
    """

    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith("data:image"):
            format, imgstr = data.split(";base64,")
            ext = format.split("/")[-1]

            imgstr = self._add_base64_padding(imgstr)

            try:
                decoded_file = base64.b64decode(imgstr)
            except (binascii.Error, ValueError) as e:
                raise serializers.ValidationError("Некорректная строка base64")

            file_name = f"uploaded.{ext}"
            data = ContentFile(decoded_file, name=file_name)

        return super().to_internal_value(data)

    def _add_base64_padding(self, s):
        return s + "=" * (-len(s) % 4)


class UserProfileSerializer(serializers.ModelSerializer):
    """Профиль пользователя с рецептами и их количеством."""

    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.ReadOnlyField(source="recipes.count")
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "avatar",
            "is_subscribed",
            "recipes",
            "recipes_count",
        ]

    def get_is_subscribed(self, obj):
        request = self.context.get("request")
        user = request.user
        if not user.is_authenticated:
            return False
        return user.subscriptions.filter(author=obj).exists()

    def get_recipes(self, obj):
        request = self.context.get("request")
        recipes_limit = request.query_params.get("recipes_limit")
        try:
            limit = int(recipes_limit)
        except (TypeError, ValueError):
            limit = None

        recipes_qs = obj.recipes.all()
        if limit:
            recipes_qs = recipes_qs[:limit]
        return RecipeAddSerializer(
            recipes_qs, many=True, context={"request": request}
        ).data


class AvatarSerializer(serializers.ModelSerializer):
    """Мини-сериализатор для обновления аватара пользователя."""

    avatar = Base64ImageField(required=True)

    class Meta:
        model = User
        fields = ["avatar"]


class CreateSubscriptionSerializer(serializers.ModelSerializer):
    """Сериализатор для подписки на пользователя."""

    author = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())

    class Meta:
        model = Subscription
        fields = ["author"]

    def validate(self, data):
        """Проверка, чтобы пользователь не подписывался сам на себя и не дублировал подписку."""
        user = self.context["request"].user
        author = data["author"]
        if user == author:
            raise serializers.ValidationError("Вы не можете подписаться на себя!")
        if user.subscriptions.filter(author=author).exists():
            raise serializers.ValidationError("Вы уже подписаны на этого пользователя.")
        return data

    def create(self, validated_data):
        """Создание подписки."""
        subscriber = self.context["request"].user
        subscription = Subscription.objects.create(
            author=validated_data["author"], subscriber=subscriber
        )
        return subscription

    def to_representation(self, instance):
        """Отображение профиля подписанного пользователя."""
        request = self.context.get("request")
        author = instance.author
        return UserProfileSerializer(author, context={"request": request}).data


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Регистрация нового пользователя."""

    username = serializers.CharField(
        max_length=MAX_LENGTH,
        validators=[
            RegexValidator(
                regex=r"^[A-Za-z0-9._-]+$",
                message="InvalidU$ername",
            ),
            UniqueValidator(
                queryset=User.objects.all(), message="Такой username уже существует."
            ),
        ],
    )
    email = serializers.EmailField(validators=[])
    password = serializers.CharField(write_only=True)
    first_name = serializers.CharField(
        max_length=MAX_LENGTH,
        validators=[
            MaxLengthValidator(MAX_LENGTH),
        ],
    )
    last_name = serializers.CharField(
        max_length=MAX_LENGTH,
        validators=[
            MaxLengthValidator(MAX_LENGTH),
        ],
    )

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "password",
            "first_name",
            "last_name",
        ]

    def validate_email(self, value):
        email_lower = value.lower()
        for user in User.objects.all():
            similarity = difflib.SequenceMatcher(
                None, email_lower, user.email.lower()
            ).ratio()
            if similarity >= 0.8:
                raise serializers.ValidationError(
                    "Пользователь с похожей почтой уже зарегистрирован."
                )
        return value

    def validate(self, data):
        return data

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user


class UserResponseSerializer(serializers.ModelSerializer):
    """Форма вывода определенных данных о пользователях."""

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
        ]


class LoginSerializer(serializers.Serializer):
    """Обработка данных пользователя при входе в аккаунт."""

    email = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, data):
        email = data.get("email")
        password = data.get("password")

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError("Пользователь с таким email не найден.")

        if not user.check_password(password):
            raise serializers.ValidationError("Неправильный пароль.")

        data["user"] = user
        return data


class SetPasswordSerializer(serializers.Serializer):
    """Смена пароля."""

    current_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)

    def validate_current_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Текущий пароль указан неверно.")
        return value

    def validate_new_password(self, value):
        return value


class UserSubscriptionSerializer(serializers.ModelSerializer):
    """Серилизатор для вывода данных о пользователе с подпиской."""

    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "avatar",
            "is_subscribed",
        ]

    def get_is_subscribed(self, obj):
        request = self.context.get("request")
        user = request.user
        if not user.is_authenticated:
            return False
        return user.subscriptions.filter(author=obj).exists()


class ShortIngredientsSerializer(serializers.ModelSerializer):
    """Краткий сериализатор ингредиентов для отображения."""

    class Meta:
        model = Ingredient
        fields = ["id", "name", "measurement_unit"]
        read_only_fields = ["id"]


class IngredientInputSerializer(serializers.Serializer):
    """Создание и изменение ингридиентов администратором."""

    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(),
        source="ingredient",
        required=True,
        help_text="Идентификатор ингредиента",
    )
    amount = serializers.IntegerField(
        min_value=MIN_VALUE,
        max_value=MAX_VALUE,
        required=True,
        help_text="Количество ингредиента",
    )


class RecipeIngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для ингредиентов в рецепте."""

    id = serializers.ReadOnlyField(source="ingredient.id")
    name = serializers.ReadOnlyField(source="ingredient.name")
    measurement_unit = serializers.ReadOnlyField(source="ingredient.measurement_unit")
    amount = serializers.IntegerField(min_value=MIN_VALUE, max_value=MAX_VALUE)

    class Meta:
        model = RecipeIngredient
        fields = ["id", "name", "measurement_unit", "amount"]


class RecipeResponseSerializer(serializers.ModelSerializer):
    """Представление рецептов согласно схеме."""

    author = UserSerializer(read_only=True)
    ingredients = RecipeIngredientSerializer(
        source="ingredients_amounts",
        many=True,
        read_only=True,
    )
    image = Base64ImageField(required=False)
    cooking_time = serializers.IntegerField(
        min_value=MIN_COOKING_TIME, max_value=MAX_COOKING_TIME
    )

    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = [
            "id",
            "author",
            "name",
            "image",
            "text",
            "ingredients",
            "cooking_time",
            "is_favorited",
            "is_in_shopping_cart",
        ]

    def get_is_favorited(self, obj):
        user = self.context["request"].user
        if not user.is_authenticated:
            return False
        return obj.favorited_by.filter(user=user).exists()

    def get_is_in_shopping_cart(self, obj):
        user = self.context["request"].user
        if not user.is_authenticated:
            return False
        return obj.in_shopping_carts.filter(user=user).exists()

    def create(self, validated_data):
        ingredients_data = validated_data.pop("ingredients", [])
        recipe = super().create(validated_data)
        self._create_ingredients(recipe, ingredients_data)
        return recipe

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop("ingredients", None)
        recipe = super().update(instance, validated_data)
        if ingredients_data is not None:
            self._update_ingredients(recipe, ingredients_data)
        return recipe


class RecipeAddSerializer(serializers.ModelSerializer):
    """Добавление рецепта согласно схеме."""

    class Meta:
        model = Recipe
        fields = [
            "id",
            "name",
            "image",
            "cooking_time",
        ]


class RecipeSerializer(serializers.ModelSerializer):
    """Основной сериализатор для рецептов."""

    author = UserSerializer(read_only=True)
    ingredients = IngredientInputSerializer(many=True, write_only=True, required=False)
    image = Base64ImageField(required=False)
    cooking_time = serializers.IntegerField(
        min_value=MIN_COOKING_TIME, max_value=MAX_COOKING_TIME
    )

    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = [
            "id",
            "author",
            "name",
            "image",
            "text",
            "ingredients",
            "cooking_time",
            "is_favorited",
            "is_in_shopping_cart",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["ingredients"] = RecipeIngredientSerializer(
            instance.ingredients_amounts.all(), many=True
        ).data
        return data

    def get_is_favorited(self, obj):
        user = self.context["request"].user
        if not user.is_authenticated:
            return False
        return obj.favorited_by.filter(user=user).exists()

    def get_is_in_shopping_cart(self, obj):
        user = self.context["request"].user
        if not user.is_authenticated:
            return False
        return obj.in_shopping_carts.filter(user=user).exists()

    def validate(self, data: Dict) -> Dict:
        """Проверка данных перед созданием/обновлением."""
        name = data.get("name")
        if name is None:
            raise serializers.ValidationError("Название рецепта обязательно.")

        ingredients = data.get("ingredients")
        if not ingredients:
            raise serializers.ValidationError(
                "Список ингредиентов не может быть пустым!"
            )

        for item in ingredients:
            if "ingredient" not in item:
                raise serializers.ValidationError(
                    f"Элемент {item} не содержит ключ 'ingredient'."
                )

        ingredient_ids = [
            (
                item["ingredient"].id
                if hasattr(item["ingredient"], "id")
                else item["ingredient"]
            )
            for item in ingredients
        ]

        existing_ids = set(
            Ingredient.objects.filter(id__in=ingredient_ids).values_list(
                "id", flat=True
            )
        )

        missing_ids = set(ingredient_ids) - existing_ids
        if missing_ids:
            raise serializers.ValidationError(
                f"Некоторые ингредиенты не найдены: {missing_ids}"
            )

        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError("Ингредиенты должны быть уникальными!")

        if "image" not in self.initial_data or not self.initial_data.get("image"):
            raise ValidationError("Поле 'image' обязательно при создании рецепта.")

        return data

    def _create_ingredients(self, recipe: Recipe, ingredients_data: List[Dict]) -> None:
        """Создать связи ингредиентов для рецепта."""
        ingredients_bulk = []
        RecipeIngredient.objects.bulk_create(ingredients_bulk)

    def _update_ingredients(self, recipe: Recipe, ingredients_data: List[Dict]) -> None:
        """Обновить связи ингредиентов."""
        recipe.ingredients_amounts.all().delete()
        self._create_ingredients(recipe, ingredients_data)

    def create(self, validated_data: Dict) -> Recipe:
        """Создать рецепт с ингредиентами."""
        ingredients_data = validated_data.pop("ingredients", [])
        recipe = Recipe.objects.create(**validated_data)
        self._create_ingredients(recipe, ingredients_data)
        return recipe

    def update(self, instance: Recipe, validated_data: Dict) -> Recipe:
        """Обновить рецепт и ингредиенты."""
        ingredients_data = validated_data.pop("ingredients", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if ingredients_data is not None:
            self._update_ingredients(instance, ingredients_data)

        return instance


class FavoriteResponseSerializer(serializers.ModelSerializer):
    """Представление рецептов в избранном согласно схеме."""

    class Meta:
        model = Recipe
        fields = ["id", "name", "image", "cooking_time"]


class FavoriteCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для добавления рецепта в избранное."""

    recipe = serializers.PrimaryKeyRelatedField(queryset=Recipe.objects.all())

    class Meta:
        model = Favorite
        fields = ["recipe"]

    def validate(self, data):
        user = self.context["request"].user
        recipe = data["recipe"]
        if user.favorites.filter(recipe=recipe).exists():
            raise serializers.ValidationError("Этот рецепт уже в избранном.")
        return data

    def create(self, validated_data):
        user = self.context["request"].user
        favorite = user.favorites.get_or_create(recipe=validated_data["recipe"])
        return favorite


class ShoppingListCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для добавления рецепта в список покупок."""

    recipe = serializers.PrimaryKeyRelatedField(queryset=Recipe.objects.all())

    class Meta:
        model = ShoppingList
        fields = ["recipe"]

    def validate(self, data):
        user = self.context["request"].user
        recipe = data["recipe"]
        if user.shopping_carts.filter(recipe=recipe).exists():
            raise serializers.ValidationError("Этот рецепт уже в списке покупок.")
        return data

    def create(self, validated_data):
        user = self.context["request"].user
        shopping_item = user.shopping_carts.get_or_create(
            recipe=validated_data["recipe"]
        )
        return shopping_item
