"""
Premissas de entrada do simulador — espelham as CÉLULAS DE INPUT da aba
'Dados do Cliente'. Tudo que o usuário informa no formulário Flask vira
um objeto Premissas; nenhuma regra de cálculo mora aqui.
"""
from dataclasses import dataclass, field


@dataclass
class Premissas:
    # --- Faturamento mensal ---
    fat_comercio: float          # B10
    fat_servicos: float          # B11
    fat_sem_nota: float = 0.0    # B12

    # RBT12 (receita bruta dos últimos 12 meses).
    # NOTA: na planilha B14 está CRAVADO (1.709.693,51) e NÃO é B13*12.
    # Aqui ele é um input explícito — que é o correto para um simulador.
    rbt12: float = 0.0           # B14

    # --- Despesas / custos operacionais ---
    compras_revenda: float = 0.0            # B32
    outras_desp_dedutiveis: float = 0.0     # B33
    desp_aluguel: float = 0.0               # B34
    desp_mat_consumo: float = 0.0           # B35
    desp_mat_limpeza: float = 0.0           # B36
    desp_energia: float = 0.0               # B37
    desp_financeiras: float = 0.0           # B38
    desp_combustivel: float = 0.0           # B39
    desp_alimentacao: float = 0.0           # B40
    outras_desp_operacionais: float = 0.0   # B41

    # --- Base de créditos PIS/COFINS (bloco Controle de Créditos) ---
    # Bases sobre as quais incidem 1,65% (PIS) e 7,6% (COFINS).
    bases_credito: list = field(default_factory=list)  # C18:D28

    # --- Folha ---
    salario_bruto: float = 0.0   # B45  (total da folha)
    ticket_alim: float = 0.0     # B46

    # --- Alíquotas / parâmetros ---
    icms: float = 0.12           # B47
    iss: float = 0.04            # B48
    inss_patronal: float = 0.20  # B49
    rat: float = 0.03            # B50
    sistema_s: float = 0.063     # B51

    @property
    def fat_total(self) -> float:
        return self.fat_comercio + self.fat_servicos + self.fat_sem_nota  # B13