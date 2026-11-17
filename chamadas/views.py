"""Camada de interface: as views só coletam e mostram dados; as regras ficam em regras.py."""

from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from . import regras
from .models import Turma
from .perfis import coordenacao_obrigatoria, eh_coordenacao


@login_required
def menu(request):
    turmas = Turma.objects.filter(ativa=True)
    return render(request, "chamadas/menu.html", {"turmas": turmas, "coordenacao": eh_coordenacao(request.user)})


@login_required
def chamada(request, turma_id):
    turma = get_object_or_404(Turma, pk=turma_id, ativa=True)
    criancas = turma.criancas.filter(ativa=True)
    hoje = timezone.localdate()
    marcacoes = {}

    if request.method == "POST":
        for c in criancas:
            valor = request.POST.get(f"crianca_{c.id}")
            if valor in ("p", "f"):
                marcacoes[c.id] = valor == "p"
        try:
            data = date.fromisoformat(request.POST.get("data", ""))
            regras.registrar_chamada(turma, data, request.user, marcacoes)
        except ValueError:
            messages.error(request, "Informe uma data válida.")
        except ValidationError as erro:
            messages.error(request, " ".join(erro.messages))
        else:
            messages.success(request, "Chamada salva.")
            return redirect(f"{reverse('alertas')}?turma={turma.id}")

    return render(
        request,
        "chamadas/chamada.html",
        {"turma": turma, "criancas": criancas, "hoje": hoje, "marcacoes": marcacoes},
    )


def _turma_escolhida(request):
    turmas = Turma.objects.filter(ativa=True)
    turma = turmas.filter(pk=request.GET.get("turma") or 0).first() or turmas.first()
    return turmas, turma


@login_required
def alertas(request):
    """Crianças com faltas seguidas (RF02). Educador e coordenação podem ver."""
    turmas, turma = _turma_escolhida(request)
    em_alerta = regras.criancas_em_alerta(turma) if turma else []
    return render(
        request,
        "chamadas/alertas.html",
        {
            "turmas": turmas,
            "turma": turma,
            "em_alerta": em_alerta,
            "limite": regras.LIMITE_FALTAS_SEGUIDAS,
            "coordenacao": eh_coordenacao(request.user),
        },
    )


@coordenacao_obrigatoria
def relatorio(request):
    """Relatório mensal de frequência por turma (RF03). Só a coordenação acessa."""
    turmas, turma = _turma_escolhida(request)
    hoje = timezone.localdate()
    try:
        ano, mes = (int(x) for x in request.GET.get("mes", f"{hoje:%Y-%m}").split("-"))
        date(ano, mes, 1)
    except ValueError:
        ano, mes = hoje.year, hoje.month
    dados = regras.relatorio_mensal(turma, ano, mes) if turma else None
    alerta_ids = {c.id for c, _ in regras.criancas_em_alerta(turma)} if turma else set()
    return render(
        request,
        "chamadas/relatorio.html",
        {"turmas": turmas, "turma": turma, "mes": f"{ano:04d}-{mes:02d}", "dados": dados, "alerta_ids": alerta_ids},
    )
