from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from chamadas.seguranca import LoginComBloqueioForm

urlpatterns = [
    path("admin/", admin.site.urls),
    path("entrar/", auth_views.LoginView.as_view(authentication_form=LoginComBloqueioForm), name="login"),
    path("sair/", auth_views.LogoutView.as_view(), name="logout"),
    path("", include("chamadas.urls")),
]
