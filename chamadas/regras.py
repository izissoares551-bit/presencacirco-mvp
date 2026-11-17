"""
Camada de regras de negócio.

As telas não acessam o banco diretamente: passam por estas funções.
Para mudar o alerta de 3 para 2 faltas, basta alterar LIMITE_FALTAS_SEGUIDAS.
"""

from collections import OrderedDict

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import Chamada, Crianca, Presenca

LIMITE_FALTAS_SEGUIDAS = 3


def faltas_seguidas(crianca):
    """Conta as faltas consecutivas mais recentes da criança, nas chamadas da turma (RF02)."""
    presencas = (
        Presenca.objects.filter(crianca=crianca, chamada__turma=crianca.turma)
        .order_by("-chamada__data")
        .values_list("presente", flat=True)
    )
    contagem = 0
    for presente in presencas:
        if presente:  # uma presença interrompe a contagem
            break
        contagem += 1
    return contagem


def criancas_em_alerta(turma, limite=LIMITE_FALTAS_SEGUIDAS):
    """Lista (criança, nº de faltas seguidas) com faltas seguidas >= limite (RF02)."""
    resultado = []
    for crianca in turma.criancas.filter(ativa=True):
        total = faltas_seguidas(crianca)
        if total >= limite:
            resultado.append((crianca, total))
    return resultado


def relatorio_mensal(turma, ano, mes):
    """Presenças e faltas de cada criança da turma no mês escolhido (RF03)."""
    chamadas = Chamada.objects.filter(turma=turma, data__year=ano, data__month=mes)
    linhas = OrderedDict()
    for crianca in Crianca.objects.filter(turma=turma).order_by("nome"):
        linhas[crianca] = {"presencas": 0, "faltas": 0}
    for p in Presenca.objects.filter(chamada__in=chamadas).select_related("crianca"):
        linha = linhas.setdefault(p.crianca, {"presencas": 0, "faltas": 0})
        linha["presencas" if p.presente else "faltas"] += 1
    return {"total_chamadas": chamadas.count(), "linhas": linhas}


@transaction.atomic
def registrar_chamada(turma, data, usuario, marcacoes):
    """Valida e grava a chamada (RF01).

    marcacoes: dicionário {id_da_crianca: True (presente) ou False (falta)}.
    """
    if data > timezone.localdate():
        raise ValidationError("A data da chamada não pode ser futura.")
    if Chamada.objects.filter(turma=turma, data=data).exists():
        raise ValidationError("Já existe uma chamada desta turma nesta data.")

    criancas = list(turma.criancas.filter(ativa=True))
    ids_da_turma = {c.id for c in criancas}
    if not set(marcacoes) <= ids_da_turma:
        raise ValidationError("Há criança que não pertence a esta turma.")
    faltando = len(ids_da_turma - set(marcacoes))
    if faltando:
        raise ValidationError(f"Falta marcar {faltando} criança(s). Marque todas para salvar.")

    chamada = Chamada.objects.create(turma=turma, data=data, registrada_por=usuario)
    Presenca.objects.bulk_create(
        Presenca(chamada=chamada, crianca=c, presente=marcacoes[c.id]) for c in criancas
    )
    return chamada
