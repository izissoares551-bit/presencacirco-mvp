"""Perfis de acesso: educador e coordenação (grupos do Django)."""

from django.contrib.auth.decorators import user_passes_test

GRUPO_EDUCADOR = "educador"
GRUPO_COORDENACAO = "coordenacao"


def eh_coordenacao(usuario):
    return usuario.is_authenticated and (
        usuario.is_superuser or usuario.groups.filter(name=GRUPO_COORDENACAO).exists()
    )


def coordenacao_obrigatoria(view):
    """Bloqueia a view para quem não é da coordenação (verificado no servidor)."""
    return user_passes_test(eh_coordenacao, login_url=None)(view)
