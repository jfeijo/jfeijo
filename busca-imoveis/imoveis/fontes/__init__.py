from .grupozap import Zap, VivaReal
from .nextjs import OLX
from .imobiliarias import QuintoAndarAPI, Guarida, Auxiliadora

# Funcionam de servidor na nuvem: quintoandar, guarida, auxiliadora.
# zap, vivareal e olx bloqueiam IPs de nuvem (Cloudflare); podem funcionar rodando de casa.
FONTES = {f.nome: f for f in (QuintoAndarAPI, Guarida, Auxiliadora, Zap, VivaReal, OLX)}
PADRAO = ["quintoandar", "guarida", "auxiliadora"]
