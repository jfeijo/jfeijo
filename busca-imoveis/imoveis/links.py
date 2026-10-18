"""Links prontos de busca em todos os portais e imobiliárias, por bairro.

Serve para conferir à mão o que os coletores automáticos não alcançam
(imobiliárias locais, Imovelweb, grupos de Facebook etc.).
"""
from __future__ import annotations

from html import escape
from urllib.parse import quote_plus

from .modelo import normalizar


def _slug(t: str) -> str:
    return normalizar(t).replace(" ", "-")


PORTAIS = {
    "ZAP Imóveis": lambda c, b, f: (
        f"https://www.zapimoveis.com.br/aluguel/{'imoveis' if f['casa'] else 'apartamentos'}/rs+{_slug(c)}++{_slug(b)}/"
        f"?areaMinima={f['area']}&precoMaximo={f['preco']}"),
    "VivaReal": lambda c, b, f: (
        f"https://www.vivareal.com.br/aluguel/rio-grande-do-sul/{_slug(c)}/bairros/{_slug(b)}/"
        f"?areaMinima={f['area']}&precoMaximo={f['preco']}"),
    "QuintoAndar": lambda c, b, f: f"https://www.quintoandar.com.br/alugar/imovel/{_slug(b)}-{_slug(c)}-rs-brasil",
    "Imovelweb": lambda c, b, f: (
        f"https://www.imovelweb.com.br/{'imoveis' if f['casa'] else 'apartamentos'}-aluguel-{_slug(b)}-{_slug(c)}.html"),
    "Wimóveis": lambda c, b, f: (
        f"https://www.wimoveis.com.br/{'imoveis' if f['casa'] else 'apartamentos'}-aluguel-{_slug(b)}-{_slug(c)}.html"),
    "OLX": lambda c, b, f: f"https://www.olx.com.br/imoveis/aluguel/estado-rs?q={quote_plus(b + ' ' + c)}",
    "Chaves na Mão": lambda c, b, f: (
        f"https://www.chavesnamao.com.br/{'imoveis' if f['casa'] else 'apartamentos'}-para-alugar/rs-{_slug(c)}/{_slug(b)}/"),
    "Loft": lambda c, b, f: f"https://loft.com.br/alugar/{_slug(c)}-rs/{_slug(b)}",
    "MGF Imóveis": lambda c, b, f: f"https://www.mgfimoveis.com.br/aluguel/{'casa' if f['casa'] else 'apartamento'}/rs-{_slug(c)}-{_slug(b)}",
    "Google": lambda c, b, f: "https://www.google.com/search?q=" + quote_plus(
        f"{'casa' if f['casa'] else 'apartamento'} para alugar {b} {c} {f['area']}m2"),
}

# Imobiliárias com carteira grande de locação na região. Os sites mudam de busca com frequência,
# então os links levam à página de locação; filtre lá por bairro / área / preço.
IMOBILIARIAS = {
    "Porto Alegre": [
        ("Auxiliadora Predial", "https://www.auxiliadorapredial.com.br/alugar"),
        ("Foxter Cia Imobiliária", "https://www.foxterciaimobiliaria.com.br/"),
        ("Guarida Imóveis", "https://www.guarida.com.br/"),
        ("Crédito Real", "https://www.creditoreal.com.br/"),
        ("Ducati Imóveis", "https://www.ducati.com.br/"),
        ("Imobiliárias de POA no Wimóveis", "https://www.wimoveis.com.br/corretores-porto-alegre-rs.html"),
    ],
    "Nova Petrópolis": [
        ("Imobiliária Pinotti", "https://www.google.com/search?q=Imobili%C3%A1ria+Pinotti+Nova+Petr%C3%B3polis+aluguel"),
        ("MGF Imóveis — Nova Petrópolis", "https://www.mgfimoveis.com.br/aluguel/casa/rs-nova-petropolis"),
        ("Imobiliárias no Google Maps", "https://www.google.com/maps/search/imobili%C3%A1ria+Nova+Petr%C3%B3polis+RS"),
        ("Grupos de aluguel no Facebook", "https://www.facebook.com/search/groups/?q=aluguel%20nova%20petr%C3%B3polis"),
    ],
}


def gerar_html(config: dict) -> str:
    teto = max(config["orcamento"]["maximo"], config["orcamento"].get("teto_flexivel_poa", 0))
    blocos = []
    for c in config["cidades"].values():
        casa = any(t in ("casa", "sobrado") for t in c["tipos"])
        filtro = {"area": c["area_minima"], "preco": int(teto), "casa": casa}
        linhas = []
        for bairro, peso in sorted(c["bairros"].items(), key=lambda x: -x[1]):
            links = " · ".join(
                f'<a href="{escape(fn(c["nome"], bairro, filtro))}" target="_blank" rel="noopener">{escape(nome)}</a>'
                for nome, fn in PORTAIS.items())
            linhas.append(f"<tr><td><b>{escape(bairro)}</b><br><small>peso {peso}</small></td><td>{links}</td></tr>")
        imob = "".join(
            f'<li><a href="{escape(u)}" target="_blank" rel="noopener">{escape(n)}</a></li>'
            for n, u in IMOBILIARIAS.get(c["nome"], []))
        blocos.append(
            f"<h2>{escape(c['nome'])}</h2><h3>Imobiliárias</h3><ul>{imob}</ul>"
            f"<h3>Portais por bairro</h3><table>{''.join(linhas)}</table>")
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Links de busca</title>
<style>body{{font-family:system-ui,sans-serif;max-width:900px;margin:auto;padding:16px;line-height:1.5}}
td{{border-top:1px solid #ddd;padding:8px;vertical-align:top}}a{{color:#0b5cad}}</style></head>
<body><h1>Links de busca — aluguel</h1>
<p>Filtros pré-aplicados quando o portal aceita: área ≥ {config['cidades']['porto_alegre']['area_minima']} m², até R$ {int(teto)}.</p>
{''.join(blocos)}</body></html>"""
