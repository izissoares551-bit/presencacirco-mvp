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


class TelasEAcessoTeste(TestCase):
    """Testes das telas e do controle de acesso por perfil (RF01, RF02, RF03, RNF01)."""

    def setUp(self):
        from django.contrib.auth.models import Group

        self.educadora = get_user_model().objects.create_user("educadora.teste", password="senha-forte-123")
        self.educadora.groups.add(Group.objects.get(name="educador"))
        self.coordenacao = get_user_model().objects.create_user("coordenacao.teste", password="senha-forte-123")
        self.coordenacao.groups.add(Group.objects.get(name="coordenacao"))
        self.turma = Turma.objects.create(nome="Turma Manhã", dia_horario="Seg e Qua, 9h")
        self.ana = Crianca.objects.create(
            nome="Ana", data_nascimento=date(2015, 1, 10), telefone_responsavel="11911110000", turma=self.turma
        )
        self.bruno = Crianca.objects.create(
            nome="Bruno", data_nascimento=date(2014, 6, 3), telefone_responsavel="11922220000", turma=self.turma
        )

    def test_sem_login_vai_para_tela_de_acesso(self):
        resposta = self.client.get("/")
        self.assertRedirects(resposta, "/entrar/?next=/")

    def test_login_invalido_mostra_mensagem_generica(self):
        resposta = self.client.post("/entrar/", {"username": "educadora.teste", "password": "errada"})
        self.assertContains(resposta, "Usuário ou senha inválidos")

    def test_educadora_registra_chamada(self):
        self.client.force_login(self.educadora)
        resposta = self.client.post(
            f"/chamada/{self.turma.id}/",
            {"data": "2026-10-21", f"crianca_{self.ana.id}": "p", f"crianca_{self.bruno.id}": "f"},
            follow=True,
        )
        self.assertContains(resposta, "Chamada salva")
        self.assertEqual(Presenca.objects.filter(presente=True).count(), 1)
        self.assertEqual(Presenca.objects.filter(presente=False).count(), 1)

    def test_chamada_incompleta_e_recusada(self):
        self.client.force_login(self.educadora)
        resposta = self.client.post(
            f"/chamada/{self.turma.id}/", {"data": "2026-10-21", f"crianca_{self.ana.id}": "p"}
        )
        self.assertContains(resposta, "Falta marcar 1 criança")
        self.assertEqual(Chamada.objects.count(), 0)

    def test_segunda_chamada_na_mesma_data_e_recusada(self):
        self.client.force_login(self.educadora)
        dados = {"data": "2026-10-21", f"crianca_{self.ana.id}": "p", f"crianca_{self.bruno.id}": "p"}
        self.client.post(f"/chamada/{self.turma.id}/", dados)
        resposta = self.client.post(f"/chamada/{self.turma.id}/", dados)
        self.assertContains(resposta, "Já existe uma chamada")
        self.assertEqual(Chamada.objects.count(), 1)

    def test_educadora_nao_abre_relatorio_nem_pela_url(self):
        self.client.force_login(self.educadora)
        self.assertEqual(self.client.get("/relatorio/").status_code, 403)

    def test_coordenacao_abre_relatorio(self):
        self.client.force_login(self.coordenacao)
        resposta = self.client.get(f"/relatorio/?turma={self.turma.id}&mes=2026-10")
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "Ana")

    def test_telefone_do_responsavel_so_aparece_para_coordenacao(self):
        for dia in (1, 5, 7):
            Chamada.objects.create(turma=self.turma, data=date(2026, 10, dia), registrada_por=self.educadora)
        for chamada in Chamada.objects.all():
            Presenca.objects.create(chamada=chamada, crianca=self.ana, presente=False)
        self.client.force_login(self.educadora)
        resposta = self.client.get("/alertas/")
        self.assertContains(resposta, "Ana")
        self.assertNotContains(resposta, "11911110000")
        self.client.force_login(self.coordenacao)
        self.assertContains(self.client.get("/alertas/"), "11911110000")

    def test_nome_com_script_aparece_como_texto(self):
        self.ana.nome = "<script>alert(1)</script>"
        self.ana.save()
        self.client.force_login(self.educadora)
        resposta = self.client.get(f"/chamada/{self.turma.id}/")
        self.assertNotContains(resposta, "<script>alert(1)</script>")
        self.assertContains(resposta, "&lt;script&gt;alert(1)&lt;/script&gt;")
