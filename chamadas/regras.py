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


def _contar_faltas_seguidas(sequencia):
    """Conta as faltas do início da sequência (da chamada mais recente para a mais antiga).

    Uma presença interrompe a contagem. Função pura, sem acesso ao banco.
    """
    contagem = 0
    for presente in sequencia:
        if presente:
            break
        contagem += 1
    return contagem


def faltas_seguidas(crianca):
    """Faltas consecutivas mais recentes de uma criança, nas chamadas da turma (RF02)."""
    sequencia = (
        Presenca.objects.filter(crianca=crianca, chamada__turma=crianca.turma)
        .order_by("-chamada__data")
        .values_list("presente", flat=True)
    )
    return _contar_faltas_seguidas(sequencia)


def criancas_em_alerta(turma, limite=LIMITE_FALTAS_SEGUIDAS):
    """Lista (criança, nº de faltas seguidas) com faltas seguidas >= limite (RF02).

    Busca todas as presenças da turma em UMA consulta, já ordenadas por criança e data,
    em vez de uma consulta por criança (evita o problema N+1).
    """
    linhas = (
        Presenca.objects.filter(chamada__turma=turma, crianca__turma=turma, crianca__ativa=True)
        .order_by("crianca_id", "-chamada__data")
        .values_list("crianca_id", "presente")
    )
    sequencias = {}
    for crianca_id, presente in linhas:
        sequencias.setdefault(crianca_id, []).append(presente)

    totais = {cid: _contar_faltas_seguidas(seq) for cid, seq in sequencias.items()}
    ids = [cid for cid, total in totais.items() if total >= limite]
    criancas = Crianca.objects.in_bulk(ids)
    return sorted(((criancas[cid], totais[cid]) for cid in ids), key=lambda par: par[0].nome)


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
