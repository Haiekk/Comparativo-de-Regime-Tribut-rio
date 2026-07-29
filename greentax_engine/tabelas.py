ANEXO_I = [   # Comércio (venda de peças)
    (0.00,         0.040,   0.00),
    (180_000.01,   0.073,   5_940.00),
    (360_000.01,   0.095,   13_860.00),
    (720_000.01,   0.107,   22_500.00),
    (1_800_000.01, 0.143,   87_300.00),
    (3_600_000.01, 0.190,   378_000.00),
]

ANEXO_III = [  # Serviços (instalação, reparos e manutenção)
    (0.00,         0.060,   0.00),
    (180_000.01,   0.112,   9_360.00),
    (360_000.01,   0.132,   17_640.00),
    (720_000.01,   0.160,   35_640.00),
    (1_800_000.01, 0.210,   125_640.00),
    (3_600_000.01, 0.330,   648_000.00),
]

LIMITE_SIMPLES = 4_800_000.00        # teto: acima disso a empresa é desenquadrada
SUBLIMITE_ICMS_ISS_SP = 3_600_000.00  # sublimite (SP): ICMS/ISS passam a ser recolhidos por fora do DAS

PIS_CUMULATIVO = 0.0065      # Lucro Presumido (sem crédito)
COFINS_CUMULATIVO = 0.03
PIS_NAO_CUMULATIVO = 0.0165  # Lucro Real (com crédito)
COFINS_NAO_CUMULATIVO = 0.076

IRPJ_ALIQUOTA = 0.15
IRPJ_ADICIONAL = 0.10
IRPJ_ADICIONAL_LIMITE = 20_000.00   # base mensal a partir da qual incide o adicional
CSLL_ALIQUOTA = 0.09

# Bases presumidas (Lucro Presumido)
PRESUMIDO_BASE_IRPJ_COMERCIO = 0.08
PRESUMIDO_BASE_IRPJ_SERVICOS = 0.32
PRESUMIDO_BASE_CSLL_COMERCIO = 0.12
PRESUMIDO_BASE_CSLL_SERVICOS = 0.32


def faixa_simples(tabela, rbt12):

    escolhida = tabela[0]
    for minima, aliq, deduzir in tabela:
        if rbt12 >= minima:
            escolhida = (minima, aliq, deduzir)
        else:
            break
    _, aliq, deduzir = escolhida
    return aliq, deduzir