"""Carrega dados FICTÍCIOS de demonstração (turmas, crianças e usuários de teste).

Uso: python manage.py carregar_demo
A senha dos usuários de teste vem da variável de ambiente DEMO_SENHA (nunca fica no código).
Pode rodar várias vezes: não duplica dados.
"""

import os
from datetime import date, timedelta

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from chamadas import regras
from chamadas.models import Chamada, Crianca, Turma

CRIANCAS = {
    "Turma Manhã": ["Ana", "Bruno", "Carla", "Davi", "Elisa", "Felipe"],
    "Turma Tarde": ["Gabriel", "Helena", "Igor", "Júlia", "Lucas"],
}
# Histórico fictício da Turma Manhã (P = presente, F = falta), na ordem de CRIANCAS.
HISTORICO_MANHA = ["PPPPPP", "PFPPPP", "PPPFPF", "PPFPPF", "PPFPPF"]


class Command(BaseCommand):
    help = "Carrega dados fictícios de demonstração."

    def handle(self, *args, **options):
        senha = os.environ.get("DEMO_SENHA")
        if not senha or len(senha) < 8:
            raise CommandError("Defina a variável de ambiente DEMO_SENHA com pelo menos 8 caracteres.")

        usuarios = {}
        for nome, grupo in (("educadora.teste", "educador"), ("coordenacao.teste", "coordenacao")):
            usuario, criado = User.objects.get_or_create(username=nome)
            if criado:
                usuario.set_password(senha)
                usuario.save()
                usuario.groups.add(Group.objects.get(name=grupo))
            usuarios[grupo] = usuario

        turmas = {}
        for i, (nome_turma, nomes) in enumerate(CRIANCAS.items()):
            turma, _ = Turma.objects.get_or_create(
                nome=nome_turma,
                defaults={"dia_horario": ["Seg, Qua e Sex, 9h", "Ter e Qui, 14h"][i]},
            )
            turmas[nome_turma] = turma
            for j, nome in enumerate(nomes):
                Crianca.objects.get_or_create(
                    nome=nome, turma=turma,
                    defaults={"data_nascimento": date(2015, 3, j + 1), "telefone_responsavel": f"1199876543{j}"},
                )

        manha = turmas["Turma Manhã"]
        if not Chamada.objects.filter(turma=manha).exists():
            criancas = [Crianca.objects.get(nome=n, turma=manha) for n in CRIANCAS["Turma Manhã"]]
            hoje = timezone.localdate()
            for k, linha in enumerate(HISTORICO_MANHA):
                dia = hoje - timedelta(days=2 * (len(HISTORICO_MANHA) - k))
                marcacoes = {c.id: (m == "P") for c, m in zip(criancas, linha)}
                regras.registrar_chamada(manha, dia, usuarios["educador"], marcacoes)

        self.stdout.write(self.style.SUCCESS("Dados fictícios de demonstração carregados."))
