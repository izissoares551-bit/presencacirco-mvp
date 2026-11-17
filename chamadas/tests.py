from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from .models import Chamada, Crianca, Presenca, Turma
from .regras import criancas_em_alerta, faltas_seguidas, relatorio_mensal


class BaseTeste(TestCase):
    def setUp(self):
        self.educadora = get_user_model().objects.create_user("educadora.teste", password="senha-forte-123")
        self.turma = Turma.objects.create(nome="Turma Manhã", dia_horario="Seg e Qua, 9h")
        self.carla = Crianca.objects.create(
            nome="Carla", data_nascimento=date(2015, 3, 2), telefone_responsavel="11999990000", turma=self.turma
        )

    def registrar(self, dia, presente):
        chamada = Chamada.objects.create(turma=self.turma, data=dia, registrada_por=self.educadora)
        Presenca.objects.create(chamada=chamada, crianca=self.carla, presente=presente)


class FaltasSeguidasTeste(BaseTeste):
    def test_tres_faltas_seguidas_gera_alerta(self):
        self.registrar(date(2026, 10, 1), True)
        for d in (5, 7, 12):
            self.registrar(date(2026, 10, d), False)
        self.assertEqual(faltas_seguidas(self.carla), 3)
        self.assertEqual(criancas_em_alerta(self.turma), [(self.carla, 3)])

    def test_duas_faltas_nao_gera_alerta(self):
        self.registrar(date(2026, 10, 5), False)
        self.registrar(date(2026, 10, 7), False)
        self.assertEqual(criancas_em_alerta(self.turma), [])

    def test_presenca_interrompe_contagem(self):
        for d, p in ((1, False), (5, False), (7, True), (12, False)):
            self.registrar(date(2026, 10, d), p)
        self.assertEqual(faltas_seguidas(self.carla), 1)


class ChamadaTeste(BaseTeste):
    def test_uma_chamada_por_turma_e_data(self):
        Chamada.objects.create(turma=self.turma, data=date(2026, 10, 21), registrada_por=self.educadora)
        with self.assertRaises(IntegrityError):
            Chamada.objects.create(turma=self.turma, data=date(2026, 10, 21), registrada_por=self.educadora)

    def test_nao_aceita_data_futura(self):
        chamada = Chamada(turma=self.turma, data=date.today() + timedelta(days=1), registrada_por=self.educadora)
        with self.assertRaises(ValidationError):
            chamada.full_clean()


class RelatorioTeste(BaseTeste):
    def test_relatorio_conta_so_o_mes_escolhido(self):
        self.registrar(date(2026, 9, 30), False)
        self.registrar(date(2026, 10, 1), True)
        self.registrar(date(2026, 10, 5), False)
        rel = relatorio_mensal(self.turma, 2026, 10)
        self.assertEqual(rel["total_chamadas"], 2)
        self.assertEqual(rel["linhas"][self.carla], {"presencas": 1, "faltas": 1})


class SenhaTeste(BaseTeste):
    def test_senha_guardada_como_hash(self):
        self.assertTrue(self.educadora.password.startswith("pbkdf2_sha256$"))
