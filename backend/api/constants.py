POST_STATUS_DRAFT = "draft"
POST_STATUS_PUBLISHED = "published"
POST_STATUSES = [
    (POST_STATUS_DRAFT, "Черновик"),
    (POST_STATUS_PUBLISHED, "Опубликовано"),
]

DEFAULT_ZERO = 0

MIN_VALUE = 1
MAX_VALUE = 32000

MAX_PAGE_SIZE = 32000

MIN_COOKING_TIME = 1
MAX_COOKING_TIME = 32000
MIN_INGREDIENT_AMOUNT = 1
MAX_INGREDIENT_AMOUNT = 32000

ROLE_USER = "user"
ROLE_ADMIN = "admin"
ROLE_MODERATOR = "moderator"
ROLES_CHOICES = [
    (ROLE_USER, "Пользователь"),
    (ROLE_ADMIN, "Админ"),
    (ROLE_MODERATOR, "Модератор"),
]

NOTIFICATION_TYPE_FOLLOW = "follow"
NOTIFICATION_TYPE_RECIPE = "recipe"
NOTIFICATION_TYPES = [
    (NOTIFICATION_TYPE_FOLLOW, "Подписка"),
    (NOTIFICATION_TYPE_RECIPE, "Новый рецепт"),
]

MAX_LENGTH_TITLE = 255
MAX_LENGTH = 150
MAX_LENGTH_DESCRIPTION = 1000

DEFAULT_PAGE_SIZE = 10
DEFAULT_PAGE_SIZES = [10, 20, 50, 100]

MESSAGES = {
    "subscription_exists": "Вы уже подписаны на этого автора.",
    "recipe_added_to_favorites": "Рецепт добавлен в избранное.",
    "recipe_removed_from_favorites": "Рецепт удален из избранного.",
}

CATEGORY_BREAKFAST = "Завтрак"
CATEGORY_LUNCH = "Обед"
CATEGORY_DINNER = "Ужин"
CATEGORIES = [
    (CATEGORY_BREAKFAST, "Завтрак"),
    (CATEGORY_LUNCH, "Обед"),
    (CATEGORY_DINNER, "Ужин"),
]
