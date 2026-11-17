"""
Camada de regras de negócio.

As telas não acessam o banco diretamente: passam por estas funções.
Para mudar o alerta de 3 para 2 faltas, basta alterar LIMITE_FALTAS_SEGUIDAS.
"""

from collections import OrderedDict

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
