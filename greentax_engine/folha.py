from .models import Premissas


def custo_folha_simples(p: Premissas) -> float:
    salario = p.salario_bruto
    prov_13 = salario / 12
    prov_ferias = (salario * 1.3333) / 12
    fgts = salario * 0.08
    fgts_prov = (prov_13 + prov_ferias) * 0.08
    return (salario + p.ticket_alim + fgts + prov_13 + prov_ferias + fgts_prov)  # B16


def custo_folha_presumido_real(p: Premissas) -> float:
    salario = p.salario_bruto
    inss = salario * p.inss_patronal
    rat = salario * p.rat
    sistema_s = salario * p.sistema_s
    fgts = salario * 0.08
    prov_13 = salario / 12
    prov_ferias = (salario * 1.3333) / 12
    fgts_prov = (prov_13 + prov_ferias) * 0.08
    inss_prov = (prov_13 + prov_ferias) * 0.14
    return (salario + p.ticket_alim + inss + rat + sistema_s + fgts
            + prov_13 + prov_ferias + fgts_prov + inss_prov)  # C16