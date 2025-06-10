from django.urls import include, path
from rest_framework import routers

from .views import (
    UserViewSet,
    ObtainAuthTokenView,
    RecipeViewSet,
    IngredientViewSet,
    LogoutView,
    AdminViewSet,
)

router = routers.DefaultRouter()
router.register("ingredients", IngredientViewSet, basename="ingredients")
router.register("recipes", RecipeViewSet, basename="recipes")
router.register("users", UserViewSet, basename="users")
router.register("admin/users", AdminViewSet, basename="admin-users")

app_name = "api"

urlpatterns = [
    path("", include(router.urls)),
    path("auth/token/login/", ObtainAuthTokenView.as_view(), name="user-login"),
    path("auth/token/logout/", LogoutView.as_view(), name="logout"),
]
