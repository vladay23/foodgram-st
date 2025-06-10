import django_filters
from django_filters.rest_framework import FilterSet, CharFilter

from .models import Ingredient, Recipe


class IngredientFilter(FilterSet):
    """
    Фильтр для модели Ingredient по имени.
    Позволяет искать ингредиенты, начинающиеся на указанный префикс.
    """

    name = CharFilter(field_name="name", lookup_expr="istartswith")

    class Meta:
        model = Ingredient
        fields = ("name",)


class RecipeFilter(FilterSet):
    """
    Фильтр для модели Recipe.
    Позволяет фильтровать рецепты по автору, а также по наличию в избранном и корзине.
    """

    author = django_filters.NumberFilter(field_name="author")
    is_favorited = django_filters.BooleanFilter(
        method="filter_is_favorited", label="В избранном"
    )
    is_in_shopping_cart = django_filters.BooleanFilter(
        method="filter_is_in_shopping_cart", label="В корзине"
    )

    def filter_is_favorited(self, queryset, name, value):
        """
        Фильтрация рецептов, добавленных в избранное текущего пользователя.
        """
        user = getattr(self.request, "user", None)
        if value and user and user.is_authenticated:
            return queryset.filter(favorites__user=user)
        return queryset

    def filter_is_in_shopping_cart(self, queryset, name, value):
        """
        Фильтрация рецептов, добавленных в корзину текущего пользователя.
        """
        user = getattr(self.request, "user", None)
        if value and user and user.is_authenticated:
            return queryset.filter(shoppinglist__user=user)
        return queryset

    class Meta:
        model = Recipe
        fields = ("author", "is_favorited", "is_in_shopping_cart")
