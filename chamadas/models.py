"""
Camada de armazenamento: entidades do MVP (modelagem da EP2).

Usuário vem do sistema de autenticação do Django; o perfil (educador ou
coordenação) é definido por grupos.
"""

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator, RegexValidator
from django.db import models
from django.utils import timezone


# Validação no servidor (RNF02): aceita só o formato esperado, recusando símbolos como < > ; usados em ataques.
validar_nome = RegexValidator(
    r"^[A-Za-zÀ-ÖØ-öø-ÿ' -]+$",
    "Use apenas letras, espaços, hífen e apóstrofo no nome.",
)
validar_telefone = RegexValidator(
    r"^\d{10,11}$",
    "Informe o telefone com DDD, só números (10 ou 11 dígitos).",
)


class Turma(models.Model):
    nome = models.CharField(max_length=80)
    faixa_etaria = models.CharField(max_length=40, blank=True)
    dia_horario = models.CharField(max_length=80)
    ativa = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]
        constraints = [
            models.UniqueConstraint(
                fields=["nome"],
                condition=models.Q(ativa=True),
                name="nome_unico_entre_turmas_ativas",
            )
        ]

    def __str__(self):
        return self.nome


class Crianca(models.Model):
    nome = models.CharField(max_length=120, validators=[MinLengthValidator(2), validar_nome])
    data_nascimento = models.DateField()
    telefone_responsavel = models.CharField(max_length=11, validators=[validar_telefone])
    turma = models.ForeignKey(Turma, on_delete=models.PROTECT, related_name="criancas")
    ativa = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "criança"
        constraints = [
            models.UniqueConstraint(
                fields=["nome", "data_nascimento", "turma"],
                name="crianca_sem_duplicidade_na_turma",
            )
        ]

    def __str__(self):
        return self.nome


class Chamada(models.Model):
    # UUID gerado no celular: evita duplicidade no reenvio offline.
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    turma = models.ForeignKey(Turma, on_delete=models.PROTECT, related_name="chamadas")
    data = models.DateField()
    registrada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="chamadas"
    )
    criada_em = models.DateTimeField(auto_now_add=True)
    sincronizada_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-data"]
        constraints = [
            models.UniqueConstraint(fields=["turma", "data"], name="uma_chamada_por_turma_e_data")
        ]

    def clean(self):
        if self.data and self.data > timezone.localdate():
            raise ValidationError({"data": "A data da chamada não pode ser futura."})

    def __str__(self):
        return f"{self.turma} – {self.data:%d/%m/%Y}"


class Presenca(models.Model):
    chamada = models.ForeignKey(Chamada, on_delete=models.CASCADE, related_name="presencas")
    crianca = models.ForeignKey(Crianca, on_delete=models.PROTECT, related_name="presencas")
    presente = models.BooleanField()

    class Meta:
        verbose_name = "presença"
        constraints = [
            models.UniqueConstraint(fields=["chamada", "crianca"], name="uma_presenca_por_crianca_na_chamada")
        ]

    def clean(self):
        if self.crianca_id and self.chamada_id and self.crianca.turma_id != self.chamada.turma_id:
            raise ValidationError("A criança precisa pertencer à turma da chamada.")

    def __str__(self):
        return f"{self.crianca}: {'Presente' if self.presente else 'Falta'}"
