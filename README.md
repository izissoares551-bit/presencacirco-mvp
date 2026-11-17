# PresençaCirco – MVP

Sistema web (PWA) de **chamada de presença e relatório de frequência** para o **Circo Social Grajaú** (CEDECA Interlagos, São Paulo).

Projeto de Software – Curso Superior de Tecnologia em Análise e Desenvolvimento de Sistemas (Cruzeiro do Sul, EAD).
Autora: **Izis Soares dos Santos**

---

## Problema

No Circo Social Grajaú, o cadastro das crianças e o controle de frequência são feitos em papel ou planilhas. Os relatórios exigidos pela SMADS e pelo CRAS tomam horas da equipe, e as faltas seguidas (risco de evasão) são percebidas tarde.

## O que o MVP faz

| Código | Prioridade | Requisito |
|---|---|---|
| RF01 | Obrigatório | Registrar a chamada de uma turma em uma data, com um toque por criança, inclusive sem internet |
| RF02 | Obrigatório | Destacar as crianças com 3 ou mais faltas consecutivas |
| RF03 | Obrigatório | Gerar o relatório mensal de frequência por turma (só para a coordenação) |
| RF04 | Desejável | Cadastrar, editar e desativar crianças e vinculá-las a uma turma |

**Diferencial:** chamada de um toque no celular, funcionamento offline e alerta de faltas seguidas, sem treinamento e sem custo para a instituição.

**ODS 4 – Educação de Qualidade (meta 4.5):** perceber as faltas mais cedo ajuda a manter crianças em situação de vulnerabilidade nas atividades educativas.

## Arquitetura

Monolito em camadas, em uma única aplicação Django:

```
Interface (templates + PWA)  →  Regras de negócio (chamadas/regras.py)  →  Armazenamento (chamadas/models.py)
```

- As telas não acessam o banco diretamente; passam pelas regras.
- Para mudar o alerta de 3 para 2 faltas, basta alterar `LIMITE_FALTAS_SEGUIDAS` em `chamadas/regras.py`.

## Tecnologias

- Python 3.12 e Django 5.2 LTS
- PostgreSQL gerenciado em produção (via psycopg 3); SQLite no desenvolvimento
- Service Worker e IndexedDB (uso offline)
- Gunicorn e WhiteNoise (publicação)
- Testes automatizados com o `TestCase` do Django

## Estrutura do repositório

```
presencacirco-mvp/
├── chamadas/            # app principal
│   ├── models.py        # Turma, Crianca, Chamada, Presenca
│   ├── regras.py        # faltas consecutivas e relatório mensal
│   ├── admin.py         # painel para carga inicial de turmas e crianças
│   ├── tests.py         # testes das regras
│   └── migrations/
├── config/              # configurações do projeto Django
├── docs/                # protótipo das telas
├── manage.py
├── requirements.txt
└── .env.example         # modelo das variáveis de ambiente
```

## Modelo de dados

- **Turma**: nome, faixa etária, dia e horário, ativa
- **Crianca**: nome, data de nascimento, telefone do responsável, turma, ativa
- **Chamada**: id UUID (gerado no celular), turma, data, registrada por, criada em, sincronizada em
- **Presenca**: chamada, criança, presente (sim/não)

Regras garantidas no banco: uma chamada por turma e data; uma presença por criança em cada chamada; sem crianças duplicadas na mesma turma. Crianças e turmas são desativadas, nunca apagadas.

**Privacidade (LGPD):** o sistema não coleta CPF, endereço, fotos, dados de saúde ou renda.

## Como executar

Pré-requisito: Python 3.12.

```bash
git clone https://github.com/izissoares551-bit/presencacirco-mvp.git
cd presencacirco-mvp
python -m venv .venv
# Windows: .venv\Scripts\activate    |    Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Acesse http://127.0.0.1:8000/admin para cadastrar turmas e crianças.

### Testes

```bash
python manage.py test
```

### Produção

Copie `.env.example`, preencha as variáveis no serviço de hospedagem (nunca no código) e defina `DJANGO_DEBUG=False`.

## Segurança

- Login obrigatório e perfis por grupo (educador e coordenação)
- Senhas guardadas como hash PBKDF2-SHA256, com no mínimo 8 caracteres
- Cookies de sessão HttpOnly, SameSite e Secure (em produção), além de proteção CSRF
- Acesso ao banco só pelo ORM (consultas parametrizadas) e escape automático nos templates
- Segredos em variáveis de ambiente

## Situação do desenvolvimento

- [x] Estrutura do projeto, modelo de dados e regras de negócio com testes
- [ ] Tela de chamada (RF01) com funcionamento offline
- [ ] Tela de alertas e relatório mensal (RF02 e RF03)
- [ ] Controle de acesso por perfil nas telas
- [ ] Cadastro de crianças (RF04)
- [ ] Publicação e validação com o Circo Social Grajaú

Dados usados em testes e demonstrações são **fictícios**.
