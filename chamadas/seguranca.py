"""Controles de segurança do login (RNF01)."""

from django.contrib.auth.forms import AuthenticationForm
from django.core.cache import cache
from django.core.exceptions import ValidationError

LIMITE_TENTATIVAS = 5
BLOQUEIO_SEGUNDOS = 15 * 60  # 15 minutos

MENSAGEM_INVALIDO = "Usuário ou senha inválidos. Tente de novo."
MENSAGEM_BLOQUEADO = "Muitas tentativas erradas. Aguarde 15 minutos e tente de novo."


def _chave(usuario):
    return f"login-falhas:{usuario.strip().lower()}"


class LoginComBloqueioForm(AuthenticationForm):
    """Bloqueia o usuário por 15 minutos após 5 senhas erradas seguidas.

    As mensagens são genéricas: não dizem se o usuário existe ou se o erro foi na senha.
    """

    error_messages = {
        "invalid_login": MENSAGEM_INVALIDO,
        "inactive": MENSAGEM_INVALIDO,
    }

    def clean(self):
        usuario = self.cleaned_data.get("username") or ""
        chave = _chave(usuario)

        if cache.get(chave, 0) >= LIMITE_TENTATIVAS:
            raise ValidationError(MENSAGEM_BLOQUEADO, code="bloqueado")

        try:
            dados = super().clean()
        except ValidationError:
            cache.add(chave, 0, BLOQUEIO_SEGUNDOS)
            cache.incr(chave)
            raise

        cache.delete(chave)
        return dados
