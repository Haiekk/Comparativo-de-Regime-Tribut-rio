# Comparativo de Regime Tributário

Simulador web que compara os três regimes tributários brasileiros — **Simples
Nacional**, **Lucro Presumido** e **Lucro Real** — a partir das premissas
informadas pelo usuário (receitas, créditos, custos, despesas e folha), e
mostra qual deles resulta na menor carga e no maior lucro líquido, com uma DRE
comparativa lado a lado.

O motor de cálculo é escrito em **Python puro**. Toda a lógica tributária foi
migrada de uma planilha Excel para código, validada célula a célula contra a
planilha de origem, eliminando a dependência de `xlwings`/Excel e tornando o
sistema publicável em qualquer hospedagem Linux.

---

## Índice

- [Arquitetura](#arquitetura)
- [Estrutura de pastas](#estrutura-de-pastas)
- [Como rodar localmente](#como-rodar-localmente)
- [Testes](#testes)
- [Publicação no Render](#publicação-no-render)
- [Regras de negócio](#regras-de-negócio)
- [Limitações conhecidas](#limitações-conhecidas)

---

## Arquitetura

O projeto separa três camadas com responsabilidades bem definidas:

1. **Motor de cálculo** (`greentax_engine/`) — regras tributárias puras, sem
   nenhuma dependência de Flask ou da web. Recebe premissas, devolve os números
   dos três regimes. É testável isoladamente.
2. **Adaptadores e serviços** (`SERVICES/`) — a ponte entre o formulário web e o
   motor: converte os campos do formulário em premissas e expõe um ponto de
   entrada único de cálculo.
3. **Camada web** (`app.py` + `templates/`) — rotas Flask e funções de
   apresentação. Fina: recebe o formulário, chama o serviço, formata o
   resultado para os templates.

O fluxo de uma simulação:

```
Formulário (HTML)
    -> app.py (rota /premissas)
    -> SERVICES/calculo_service.processar(dados)
        -> SERVICES/premissas_adapter.montar_premissas(dados)   # form -> Premissas
        -> greentax_engine.comparar(premissas)                  # calcula os 3 regimes
    -> app.py formata (montar_resumo / montar_tabela_*)
    -> templates/resultado.html
```

---

## Estrutura de pastas

```
COMPARATIVO DE REGIME/
├── app.py                      # ponto de entrada Flask (rotas + apresentação)
├── requirements.txt            # dependências (Flask, Flask-Session, gunicorn)
├── render.yaml                 # blueprint de deploy do Render
├── .gitignore
├── README.md
│
├── greentax_engine/            # MOTOR DE CÁLCULO (Python puro)
│   ├── __init__.py             # expõe Premissas e comparar
│   ├── models.py               # dataclass Premissas (entradas)
│   ├── tabelas.py              # faixas do Simples + alíquotas + limites (dados)
│   ├── folha.py                # custo de folha por regime
│   ├── creditos.py             # créditos de PIS/COFINS
│   ├── simples.py              # Simples Nacional (Anexos I e III)
│   ├── presumido.py            # Lucro Presumido
│   ├── real.py                 # Lucro Real
│   ├── contrato.py             # monta o dicionário de saída (comparativo/dre/detalhamento)
│   └── comparador.py           # orquestra + regra dos limites do Simples
│
├── SERVICES/
│   ├── __init__.py
│   ├── utils.py                # parse_moeda, num, texto
│   ├── premissas_adapter.py    # formulário -> Premissas
│   └── calculo_service.py      # processar(dados): ponto de entrada do cálculo
│
├── static/
│   ├── css/style.css
│   ├── img/logo.png
│   └── js/app.js
│
└── templates/
    ├── base.html
    ├── index.html
    ├── novo_planejamento.html  # etapa 1: dados da empresa
    ├── premissas.html          # etapa 2: premissas financeiras
    └── resultado.html          # etapa 3: comparativo + DRE
```

---

## Como rodar localmente

Requisitos: Python 3.12+ instalado.

```bash
# 1. (opcional, recomendado) criar um ambiente virtual
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 2. instalar as dependências
pip install -r requirements.txt

# 3. rodar
python app.py
```

O site sobe em **http://127.0.0.1:5000**.

> `python app.py` usa o servidor de desenvolvimento do Flask, adequado só para
> testar na sua máquina. Em produção o app é servido pelo Gunicorn (ver
> [Publicação no Render](#publicação-no-render)).


---

## Publicação no Render

O repositório já traz um `render.yaml`. No painel do Render, use
**New → Blueprint**, conecte este repositório, e o Render lê o arquivo e
configura tudo sozinho:

- **Build:** `pip install -r requirements.txt`
- **Start:** `gunicorn app:app`
- **Variável `FLASK_SECRET_KEY`:** gerada automaticamente (`generateValue: true`)

A cada `git push` na branch `main`, o Render republica automaticamente.

### Variável de ambiente

| Variável            | Descrição                                              |
|---------------------|--------------------------------------------------------|
| `FLASK_SECRET_KEY`  | Chave para assinar os cookies de sessão. **Obrigatória em produção.** No Render é gerada automaticamente; localmente usa um valor de desenvolvimento. |

---

## Regras de negócio

O motor calcula os três regimes com base nas mesmas premissas e escolhe como
**recomendado** o de maior lucro líquido entre os elegíveis.

**Regra dos dois limites do Simples Nacional:**

- **Teto de R$ 4.800.000,00 de RBT12:** acima disso a empresa é desenquadrada e
  o Simples é *excluído* da comparação.
- **Sublimite de R$ 3.600.000,00 (SP):** entre 3,6 mi e 4,8 mi o Simples
  *permanece* na comparação, mas com um aviso de que o cálculo ainda não
  contempla o ICMS/ISS recolhido por fora do DAS.

As alíquotas, faixas e limites ficam centralizados em
`greentax_engine/tabelas.py`, versionáveis por ano de vigência.

---

## Limitações conhecidas

- **ICMS/ISS por fora do DAS** (faixa de 3,6 mi a 4,8 mi de RBT12): ainda não
  modelado; nessa faixa o valor do Simples é sinalizado por aviso como
  otimista. Melhoria futura.
- **Sessão em disco:** as sessões usam armazenamento em arquivo
  (`SESSION_TYPE = "filesystem"`). No plano gratuito do Render o disco é
  efêmero — em um reinício/republicação as sessões em andamento se perdem. Para
  tráfego real, considerar um armazenamento externo (ex.: Redis).
- **Alíquotas municipais/estaduais fixas:** ICMS, ISS e encargos de folha usam
  valores-padrão definidos no motor; não são coletados no formulário.

---

*Simulação com finalidade comparativa. Não substitui a análise de um
profissional de contabilidade.*