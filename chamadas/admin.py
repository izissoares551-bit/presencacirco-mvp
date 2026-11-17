from django.contrib import admin

from .models import Chamada, Crianca, Presenca, Turma


@admin.register(Turma)
class TurmaAdmin(admin.ModelAdmin):
    list_display = ("nome", "dia_horario", "ativa")
    list_filter = ("ativa",)


@admin.register(Crianca)
class CriancaAdmin(admin.ModelAdmin):
    list_display = ("nome", "turma", "ativa")
    list_filter = ("turma", "ativa")
    search_fields = ("nome",)


class PresencaInline(admin.TabularInline):
    model = Presenca
    extra = 0


@admin.register(Chamada)
class ChamadaAdmin(admin.ModelAdmin):
    list_display = ("turma", "data", "registrada_por", "sincronizada_em")
    list_filter = ("turma",)
    inlines = [PresencaInline]
