"""Camada de interface: as views só coletam e mostram dados; as regras ficam em regras.py."""

from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from . import regras
from .models import Turma
from .perfis import eh_coordenacao


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
            return redirect("menu")

    return render(
        request,
        "chamadas/chamada.html",
        {"turma": turma, "criancas": criancas, "hoje": hoje, "marcacoes": marcacoes},
    )
