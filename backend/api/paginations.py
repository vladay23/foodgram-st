from rest_framework.pagination import PageNumberPagination
from .constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE


class CustomPagination(PageNumberPagination):
    page_size = DEFAULT_PAGE_SIZE
    page_size_query_param = 'limit'
    max_page_size = MAX_PAGE_SIZE


class RecipesPagination(PageNumberPagination):
    """
    Пагинация для страниц рецептов.
    """

    page_size = DEFAULT_PAGE_SIZE
    page_size_query_param = "limit"
    max_page_size = MAX_PAGE_SIZE


class FavoritesPagination(PageNumberPagination):
    """
    Пагинация для страниц избранных рецептов.
    """

    page_size = DEFAULT_PAGE_SIZE
    page_size_query_param = "limit"
    max_page_size = MAX_PAGE_SIZE


class SubscriptionsPagination(PageNumberPagination):
    """
    Пагинация для страниц подписок.
    """

    page_size = DEFAULT_PAGE_SIZE
    page_size_query_param = "limit"
    max_page_size = MAX_PAGE_SIZE


class ShoppingListPagination(PageNumberPagination):
    """
    Пагинация для страниц списка покупок.
    """

    page_size = DEFAULT_PAGE_SIZE
    page_size_query_param = "limit"
    max_page_size = MAX_PAGE_SIZE
