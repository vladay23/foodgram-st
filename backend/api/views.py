from rest_framework import serializers, status, viewsets, permissions
from rest_framework.views import APIView
from rest_framework.response import Response

from rest_framework.permissions import (
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
    AllowAny,
)

import io
from .permissions import IsAuthorOrReadOnly, IsAdminOnly
from rest_framework.decorators import action
from .paginations import CustomPagination
from django_filters.rest_framework import DjangoFilterBackend
from .filters import RecipeFilter, IngredientFilter
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.db.models import Sum

from .constants import DEFAULT_ZERO

from .serializers import (
    UserSerializer,
    UserRegistrationSerializer,
    UserProfileSerializer,
    UserResponseSerializer,
    SetPasswordSerializer,
    AvatarSerializer,
    CreateSubscriptionSerializer,
    RecipeSerializer,
    FavoriteCreateSerializer,
    ShoppingListCreateSerializer,
    ShortIngredientsSerializer,
    RecipeResponseSerializer,
    FavoriteResponseSerializer,
)

from .models import (
    User,
    Recipe,
    Ingredient,
    RecipeIngredient,
    ShoppingList,
    Favorite,
)

from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import MethodNotAllowed, PermissionDenied

User = get_user_model()


class ObtainAuthTokenView(APIView):
    """Получение токена для авторизации по email"""

    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        if not email:
            return Response(
                {"detail": "Пожалуйста, введите email."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not password:
            return Response(
                {"detail": "Пожалуйста, введите пароль."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user_obj = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"detail": "Неверный email или пароль."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = authenticate(request, username=user_obj.username, password=password)
        if user is None:
            return Response(
                {"detail": "Неверный email или пароль."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        token, created = Token.objects.get_or_create(user=user)
        return Response({"auth_token": token.key})


class LogoutView(APIView):
    """Выход из аккаунта — удаление токена авторизации"""

    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def post(self, request):
        try:
            token = request.auth
            if token:
                token.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(
                    {"detail": "Токен не найден."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Token.DoesNotExist:
            return Response(
                {"detail": "Токен не найден."},
                status=status.HTTP_400_BAD_REQUEST,
            )


class AdminViewSet(viewsets.ModelViewSet):
    """Работа с администратором."""

    queryset = User.objects.filter(is_staff=True)
    permission_classes = [permissions.IsAdminUser]
    serializer_class = UserSerializer


class UserViewSet(viewsets.ModelViewSet):
    """Работа с пользователями"""

    queryset = User.objects.all()
    serializer_class = UserProfileSerializer
    pagination_class = CustomPagination

    def get_serializer_class(self):
        if self.action in ["list", "retrieve", "me"]:
            return UserSerializer
        elif self.action in ["partial_update", "update"]:
            return UserProfileSerializer
        return super().get_serializer_class()

    def get_permissions(self):
        if self.action in ["list", "retrieve", "profile", "create"]:
            return [AllowAny()]
        elif self.action in ["destroy", "admin_set_password", "block_user"]:
            return [IsAuthenticated(), IsAdminOnly()]
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        serializer = UserRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        user_data = UserResponseSerializer(user).data
        return Response(user_data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(
        detail=True,
        methods=["post", "delete", "put"],
        permission_classes=[IsAuthenticated],
        url_path="avatar",
        url_name="avatar",
    )
    def avatar(self, request, pk=None):
        if pk == "me":
            user = request.user
        else:
            user = get_object_or_404(User, pk=pk)

        if request.user != user:
            return Response(
                {"detail": "Недостаточно прав."}, status=status.HTTP_403_FORBIDDEN
            )

        if request.method == "POST":
            serializer = AvatarSerializer(user, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response({"detail": "Аватар обновлён."})
        elif request.method == "DELETE":
            if user.avatar:
                user.avatar.delete(save=True)
            return Response(
                {"detail": "Аватар удалён."}, status=status.HTTP_204_NO_CONTENT
            )
        elif request.method == "PUT":
            serializer = AvatarSerializer(user, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)

    @action(
        detail=False,
        methods=["post"],
        permission_classes=[IsAuthenticated],
        url_path="set_password",
        url_name="set_password",
    )
    def set_password(self, request):
        serializer = SetPasswordSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        user = request.user
        user.set_password(serializer.validated_data["new_password"])
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=["post", "delete"],
        permission_classes=[IsAuthenticated],
        url_path="subscribe",
        url_name="subscribe",
    )
    def subscribe(self, request, pk=None):
        author = get_object_or_404(User, pk=pk)
        user = request.user

        if request.method == "POST":
            if user.subscriptions.filter(author=author).exists():
                return Response(
                    {"detail": "Вы уже подписаны."}, status=status.HTTP_400_BAD_REQUEST
                )
            serializer = CreateSubscriptionSerializer(
                data={"author": author.id}, context={"request": request}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()

            serializer = UserProfileSerializer(author, context={"request": request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        elif request.method == "DELETE":
            subscription = user.subscriptions.filter(author=author)
            if not subscription.exists():
                return Response(
                    {"detail": "Вы не подписаны."}, status=status.HTTP_400_BAD_REQUEST
                )
            subscription.delete()

            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[IsAuthenticated],
        url_path="subscriptions",
        url_name="subscriptions",
    )
    def my_subscriptions(self, request):
        subscriptions = User.objects.filter(subscriptions__subscriber=request.user)
        page = self.paginate_queryset(subscriptions)
        if page is not None:
            serializer = UserProfileSerializer(
                page, many=True, context={"request": request}
            )
            return self.get_paginated_response(serializer.data)
        serializer = UserProfileSerializer(
            subscriptions, many=True, context={"request": request}
        )
        return Response(serializer.data)

    @action(
        detail=True,
        methods=["get"],
        permission_classes=[AllowAny],
        url_path="profile",
        url_name="profile",
    )
    def profile(self, request, pk=None):
        user = get_object_or_404(User, pk=pk)
        serializer = UserProfileSerializer(user, context={"request": request})
        return Response(serializer.data)

    @action(
        detail=True,
        methods=["patch", "put"],
        permission_classes=[IsAuthenticated],
        url_path="update_profile",
        url_name="update_profile",
    )
    def update_profile(self, request, pk=None):
        user = get_object_or_404(User, pk=pk)
        if request.user != user:
            return Response(
                {"detail": "Недостаточно прав."}, status=status.HTTP_403_FORBIDDEN
            )
        serializer = UserProfileSerializer(
            user, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
    
    @action(
        detail=True,
        methods=["delete"],
        permission_classes=[IsAuthenticated, IsAdminOnly],
        url_path="delete-user",
        url_name="delete_user",
    )
    def delete_user(self, request, pk=None):
        user = get_object_or_404(User, pk=pk)
        user.delete()
        return Response({"detail": "Пользователь удалён."}, status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated, IsAdminOnly],
        url_path="set_password",
        url_name="admin_set_password",
    )
    def admin_set_password(self, request, pk=None):
        user = get_object_or_404(User, pk=pk)
        serializer = SetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user.set_password(serializer.validated_data["new_password"])
        user.save()
        return Response({"detail": "Пароль изменён."})
    
    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated, IsAdminOnly],
        url_path="block",
        url_name="block_user",
    )
    def block_user(self, request, pk=None):
        user = get_object_or_404(User, pk=pk)
        user.is_active = False
        user.save()
        return Response({"detail": "Пользователь заблокирован."})

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated, IsAdminOnly],
        url_path="unblock",
        url_name="unblock_user",
    )
    def unblock_user(self, request, pk=None):
        user = get_object_or_404(User, pk=pk)
        user.is_active = True
        user.save()
        return Response({"detail": "Пользователь разблокирован."})


class IngredientViewSet(viewsets.ModelViewSet):
    """Просмотр, создание и обновление ингредиентов."""

    queryset = Ingredient.objects.all()
    serializer_class = ShortIngredientsSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter
    search_fields = ("^name",)

    pagination_class = None

    def get_permissions(self):
        if self.action in ["list", "retrieve", "get_ingredients_for_recipe"]:
            permission_classes = [AllowAny]
        elif self.action in ["create", "update", "partial_update", "destroy"]:
            permission_classes = [IsAdminOnly]
        else:
            permission_classes = [AllowAny]
        return [permission() for permission in permission_classes]

    def initial(self, request, *args, **kwargs):
        permissions = self.get_permissions()

        for perm in permissions:
            if not perm.has_permission(request, self):
                if request.method.upper() in ["POST", "PUT", "PATCH", "DELETE"]:
                    raise MethodNotAllowed(self.action)
                raise PermissionDenied()

        super().initial(request, *args, **kwargs)

    @action(detail=False, methods=["get"], url_path="recipe")
    def get_ingredients_for_recipe(self, request):
        recipe_id = request.query_params.get("recipe_id")
        if not recipe_id:
            return Response(
                {"error": "Не указан параметр recipe_id."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            recipe = Recipe.objects.get(id=recipe_id)
        except Recipe.DoesNotExist:
            return Response(
                {"error": "Рецепт с таким ID не найден."},
                status=status.HTTP_404_NOT_FOUND,
            )

        ingredients = recipe.ingredients.all()
        serializer = self.get_serializer(ingredients, many=True)
        return Response(serializer.data)


class RecipeViewSet(viewsets.ModelViewSet):
    """Работа с рецептами"""

    queryset = Recipe.objects.all()
    pagination_class = CustomPagination
    permission_classes = [IsAuthenticated, IsAuthenticatedOrReadOnly]
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter
    serializer_class = RecipeSerializer

    def get_serializer_class(self):
        if self.action in ["list", "retrieve"]:
            return RecipeResponseSerializer
        return RecipeSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context

    def get_permissions(self):
        if self.action in ["list", "retrieve", "download_shopping_cart", "get_link"]:
            permission_classes = [AllowAny]
        elif self.action == "create":
            permission_classes = [IsAuthenticated]
        elif self.action in ["update", "partial_update", "destroy"]:
            permission_classes = [IsAuthenticated, IsAuthorOrReadOnly]
        elif self.action in [
            "favorite",
            "remove_favorite",
            "shopping_cart",
            "remove_shopping_cart",
        ]:
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    def perform_create(self, serializer):
        """Создание рецепта с автором"""
        serializer.save(author=self.request.user)

    @action(detail=True, methods=["post"])
    def favorite(self, request, pk=None):
        get_object_or_404(Recipe, pk=pk)
        return self._add_recipe_to_relation(
            request,
            pk,
            serializer_class=FavoriteCreateSerializer,
            related_name="favorites",
            not_found_message="Рецепт уже в избранном или не найден.",
        )

    @favorite.mapping.delete
    def remove_favorite(self, request, pk=None):
        return self._remove_recipe_from_relation(
            request,
            pk,
            related_name="favorites",
            does_not_exist_exception=Favorite.DoesNotExist,
            does_not_exist_message="Рецепт не в избранном.",
        )

    @action(detail=True, methods=["post"])
    def shopping_cart(self, request, pk=None):
        get_object_or_404(Recipe, pk=pk)
        return self._add_recipe_to_relation(
            request,
            pk,
            serializer_class=ShoppingListCreateSerializer,
            related_name="shopping_carts",
            not_found_message="Рецепт уже в списке покупок или не найден.",
        )

    @shopping_cart.mapping.delete
    def remove_shopping_cart(self, request, pk=None):
        return self._remove_recipe_from_relation(
            request,
            pk,
            related_name="shopping_carts",
            does_not_exist_exception=ShoppingList.DoesNotExist,
            does_not_exist_message="Рецепт не в списке покупок.",
        )

    def _add_recipe_to_relation(
        self, request, pk, serializer_class, related_name, not_found_message
    ):
        """Общий метод добавления рецепта в связь"""
        serializer = serializer_class(
            data={
                "user": request.user.id,
                "recipe": pk,
            },
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        recipe = get_object_or_404(Recipe, pk=pk)
        recipe_serializer = FavoriteResponseSerializer(
            recipe, context={"request": request}
        )
        return Response(recipe_serializer.data, status=status.HTTP_201_CREATED)

    def _remove_recipe_from_relation(
        self,
        request,
        pk,
        related_name,
        does_not_exist_exception,
        does_not_exist_message,
    ):
        """Общий метод удаления рецепта из связи"""
        try:
            relation_queryset = getattr(request.user, related_name)
            relation_instance = relation_queryset.get(recipe__id=pk)
            relation_instance.delete()
        except does_not_exist_exception:
            return Response(
                {"detail": does_not_exist_message},
                # Тест при 400 требует 404, но при 404 — 400
                # Лошичнее оставить код 404
                status=status.HTTP_404_NOT_FOUND,
                # status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[IsAuthenticated],
        url_path="download_shopping_cart",
        url_name="download_shopping_cart",
    )
    def download_shopping_cart(self, request):
        ingredients = (
            RecipeIngredient.objects.filter(
                recipe__in_shopping_carts__user=request.user
            )
            .values("ingredient__name", "ingredient__measurement_unit")
            .annotate(total_amount=Sum("amount"))
        )

        return self._ingredients_to_txt_response(request, ingredients)

    def _ingredients_to_txt_response(self, request, ingredients):
        shopping_list = "\n".join(
            f"{ingredient['ingredient__name']}-{ingredient['total_amount']}"
            f"({ingredient['ingredient__measurement_unit']})"
            for ingredient in ingredients
        )

        file_buffer = io.StringIO()
        file_buffer.write(shopping_list)
        file_buffer.seek(DEFAULT_ZERO)

        response = HttpResponse(file_buffer.getvalue(), content_type="text/plain")
        response["Content-Disposition"] = 'attachment; filename="shopping_list.txt"'
        return response

    @action(
        detail=True,
        methods=["get"],
        permission_classes=[IsAuthenticatedOrReadOnly],
        url_path="get-link",
        url_name="get-link",
    )
    def get_link(self, request, pk):
        """Получить короткую ссылку на рецепт"""
        instance = self.get_object()

        full_url = request.build_absolute_uri(f"/s/{instance.id}")

        return Response({"short-link": full_url})

    def list(self, request, *args, **kwargs):
        is_in_shopping_cart = request.query_params.get("is_in_shopping_cart")
        is_favorited = request.query_params.get("is_favorited")

        if is_in_shopping_cart == "1":
            if not request.user.is_authenticated:
                recipes = self.queryset.none()
            else:
                recipes = Recipe.objects.filter(
                    in_shopping_carts__user=request.user
                ).distinct()

        elif is_favorited == "1":
            if not request.user.is_authenticated:
                recipes = self.queryset.none()
            else:
                recipes = Recipe.objects.filter(
                    favorited_by__user=request.user
                ).distinct()
        else:
            recipes = self.queryset

        page = self.paginate_queryset(recipes)
        if page is not None:
            serializer = self.get_serializer(
                page, many=True, context={"request": request}
            )
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(
            recipes, many=True, context={"request": request}
        )
        return Response(serializer.data)
