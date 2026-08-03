from dataclasses import dataclass, field

@dataclass
class Premissas:
    fat_comercio: float          
    fat_servicos: float          
    fat_sem_nota: float = 0.0    

    rbt12: float = 0.0           

    compras_revenda: float = 0.0            
    outras_desp_dedutiveis: float = 0.0     
    desp_aluguel: float = 0.0               
    desp_mat_consumo: float = 0.0           
    desp_mat_limpeza: float = 0.0           
    desp_energia: float = 0.0               
    desp_financeiras: float = 0.0           
    desp_combustivel: float = 0.0           
    desp_alimentacao: float = 0.0           
    outras_desp_operacionais: float = 0.0   

    bases_credito: list = field(default_factory=list)  

    salario_bruto: float = 0.0   
    ticket_alim: float = 0.0     

    icms: float = 0.12           
    iss: float = 0.04            
    inss_patronal: float = 0.20  
    rat: float = 0.03            
    sistema_s: float = 0.063     

    @property
    def fat_total(self) -> float:
        return self.fat_comercio + self.fat_servicos + self.fat_sem_nota  