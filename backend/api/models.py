from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

from .constants import MIN_VALUE, MAX_VALUE, MAX_LENGTH, MAX_LENGTH_TITLE


class User(AbstractUser):
    """
    Пользовательская модель, расширяющая AbstractUser.
    """

    avatar = models.ImageField(
        upload_to="avatars/",
        blank=True,
        null=True,
        verbose_name="Аватар",
    )

    class Meta:
        ordering = ["username"]

    def __str__(self):
        return self.username


class Subscription(models.Model):
    """
    Модель для подписок пользователей.
    """

    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="followers",
        verbose_name="Автор",
        help_text="Пользователь, на которого подписываются",
    )
    subscriber = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="subscriptions",
        verbose_name="Подписчик",
        help_text="Пользователь, который подписывается",
    )

    class Meta:
        verbose_name = "Подписка"
        verbose_name_plural = "Подписки"
        constraints = [
            models.UniqueConstraint(
                fields=["author", "subscriber"], name="unique_subscription"
            )
        ]
        ordering = ["author__username"]

    def __str__(self):
        return f"{self.subscriber} подписан на {self.author}"


class Ingredient(models.Model):
    """
    Модель для ингредиентов.
    """

    name = models.CharField(
        max_length=MAX_LENGTH,
        verbose_name="Название ингредиента",
    )
    measurement_unit = models.CharField(
        max_length=MAX_LENGTH,
        verbose_name="Единица измерения",
    )

    class Meta:
        verbose_name = "Ингредиент"
        verbose_name_plural = "Ингредиенты"
        constraints = [
            models.UniqueConstraint(
                fields=["name", "measurement_unit"], name="unique_ingredient_unit"
            )
        ]
        ordering = ["name"]

    def __str__(self):
        return f"{self.name}, {self.measurement_unit}"


class Recipe(models.Model):
    """
    Модель для рецептов.
    """

    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="recipes",
        verbose_name="Автор рецепта",
    )
    name = models.CharField(
        max_length=MAX_LENGTH_TITLE,
        verbose_name="Название рецепта",
    )
    image = models.ImageField(
        upload_to="recipes/images/",
        verbose_name="Изображение рецепта",
        null=True,
        blank=True,
    )
    text = models.TextField(
        verbose_name="Описание рецепта",
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through="RecipeIngredient",
        related_name="recipes",
        verbose_name="Ингредиенты в рецепте",
    )
    cooking_time = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(MIN_VALUE),
            MaxValueValidator(MAX_VALUE),
        ],
        verbose_name="Время приготовления (в минутах)",
    )
    pub_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата публикации",
    )

    class Meta:
        ordering = ["-pub_date"]
        verbose_name = "Рецепт"
        verbose_name_plural = "Рецепты"

    def __str__(self):
        return self.name


class RecipeIngredient(models.Model):
    """
    Модель для связи рецепта и ингредиента с указанием количества.
    """

    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name="ingredients_amounts",
        verbose_name="Рецепт",
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name="used_in_recipes",
        verbose_name="Ингредиент",
    )
    amount = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(MIN_VALUE),
            MaxValueValidator(MAX_VALUE),
        ],
        verbose_name="Количество",
    )

    class Meta:
        verbose_name = "Ингредиент в рецепте"
        verbose_name_plural = "Ингредиенты в рецепте"
        constraints = [
            models.UniqueConstraint(
                fields=["recipe", "ingredient"],
                name="unique_recipe_ingredient",
            ),
        ]

    def __str__(self):
        return (
            f"{self.ingredient.name} ({self.amount} "
            f"{self.ingredient.measurement_unit})"
        )


class Favorite(models.Model):
    """
    Модель для избранных рецептов пользователя.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="favorites",
        verbose_name="Пользователь",
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name="favorited_by",
        verbose_name="Рецепт",
    )
    date_added = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата добавления",
    )

    class Meta:
        verbose_name = "Избранное"
        verbose_name_plural = "Избранное"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "recipe"],
                name="unique_favorite",
            ),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.recipe.name}"


class ShoppingList(models.Model):
    """
    Модель для списка покупок пользователя.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="shopping_carts",
        verbose_name="Пользователь",
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name="in_shopping_carts",
        verbose_name="Рецепт",
    )
    date_added = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата добавления",
    )

    class Meta:
        verbose_name = "Список покупок"
        verbose_name_plural = "Списки покупок"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "recipe"],
                name="unique_shopping_cart",
            ),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.recipe.name}"
