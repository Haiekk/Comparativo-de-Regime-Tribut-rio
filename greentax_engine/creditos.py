from .models import Premissas


def creditos_pis_cofins(p: Premissas):
    base = sum(p.bases_credito)
    credito_pis = base * 0.0165      # C29
    credito_cofins = base * 0.076    # D29
    return credito_pis, credito_cofins