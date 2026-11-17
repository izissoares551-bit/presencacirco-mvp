"""Perfis de acesso: educador e coordenação (grupos do Django)."""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

GRUPO_EDUCADOR = "educador"
GRUPO_COORDENACAO = "coordenacao"


def eh_coordenacao(usuario):
    return usuario.is_authenticated and (
        usuario.is_superuser or usuario.groups.filter(name=GRUPO_COORDENACAO).exists()
    )


def coordenacao_obrigatoria(view):
    """Exige login e perfil de coordenação, verificado no servidor (acesso negado = 403)."""

    @wraps(view)
    def _view(request, *args, **kwargs):
        if not eh_coordenacao(request.user):
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return login_required(_view)
