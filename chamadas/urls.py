from django.urls import path

from . import views

urlpatterns = [
    path("", views.menu, name="menu"),
    path("chamada/<int:turma_id>/", views.chamada, name="chamada"),
]
