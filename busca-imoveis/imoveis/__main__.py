"""Linha de comando.

    python -m imoveis buscar              # busca em todos os portais e gera o relatório
    python -m imoveis buscar --fontes zap vivareal --cidade porto_alegre
    python -m imoveis importar meus_imoveis.csv   # anúncios achados à mão (imobiliárias)
    python -m imoveis relatorio           # só refaz o relatorio.html
    python -m imoveis links               # gera links.html com buscas prontas em todos os portais
    python -m imoveis marcar 3fa9c1 favorito "visitar sábado"
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import yaml

from . import links, relatorio
from .avaliacao import avaliar
from .banco import Banco
from .fontes import FONTES
from .fontes.base import FonteIndisponivel, inteiro, numero
from .modelo import Imovel

RAIZ = Path(__file__).resolve().parent.parent


def carregar_config(caminho: Path) -> dict:
    with open(caminho, encoding="utf-8") as f:
        return yaml.safe_load(f)


def cmd_buscar(args, config, banco):
    cidades = {k: v for k, v in config["cidades"].items() if not args.cidade or k in args.cidade}
    fontes = args.fontes or list(FONTES)
    novos = aprovados = total = 0
    falhas = []
    for nome_fonte in fontes:
        fonte = FONTES[nome_fonte](pausa=config.get("pausa_segundos", 2.5))
        for chave_cidade, cidade_cfg in cidades.items():
            for bairro in cidade_cfg["bairros"]:
                try:
                    achados = list(fonte.buscar(cidade_cfg, bairro, config))
                except FonteIndisponivel as e:
                    falhas.append(str(e))
                    print(f"  ! {e}", file=sys.stderr)
                    if "bloqueado" in str(e) or "rede" in str(e):
                        break  # não insiste numa fonte que bloqueou
                    continue
                for im in achados:
                    if not im.url:
                        continue
                    total += 1
                    r = avaliar(im, config)
                    if banco.salvar(im, r) and r.aprovado:
                        novos += 1
                    aprovados += r.aprovado
                print(f"  {nome_fonte:12} {cidade_cfg['nome']:16} {bairro:20} {len(achados):3} anúncios")
            else:
                continue
            break
    print(f"\n{total} anúncios lidos, {aprovados} passaram nos filtros, {novos} aprovados são novos.")
    if falhas:
        print(f"{len(falhas)} buscas falharam — veja links.html para conferir essas fontes à mão.")
    cmd_relatorio(args, config, banco)


def cmd_importar(args, config, banco):
    """CSV com colunas: url,cidade,bairro,tipo,area,quartos,vagas,aluguel,condominio,iptu,titulo,descricao"""
    n = 0
    with open(args.arquivo, encoding="utf-8-sig") as f:
        for linha in csv.DictReader(f):
            if not (linha.get("url") or "").strip():
                continue
            im = Imovel(
                fonte="manual", url=linha["url"].strip(), cidade=linha.get("cidade", "Porto Alegre"),
                bairro=linha.get("bairro", ""), tipo=(linha.get("tipo") or "apartamento").strip().lower(),
                area=numero(linha.get("area")), quartos=inteiro(linha.get("quartos")),
                vagas=inteiro(linha.get("vagas")), aluguel=numero(linha.get("aluguel")),
                condominio=numero(linha.get("condominio")), iptu_mensal=numero(linha.get("iptu")),
                titulo=linha.get("titulo", ""), descricao=linha.get("descricao", ""),
            )
            r = avaliar(im, config)
            banco.salvar(im, r)
            n += 1
            situacao = "OK " if r.aprovado else "FORA"
            print(f"  {situacao} nota {r.nota:5.1f}  {im.bairro:18} {'; '.join(r.motivos_reprovacao)}")
    print(f"{n} imóveis importados.")
    cmd_relatorio(args, config, banco)


def cmd_relatorio(args, config, banco):
    saida = RAIZ / "relatorio.html"
    saida.write_text(relatorio.gerar_html(banco.aprovados()), encoding="utf-8")
    print(f"Relatório: {saida}")


def cmd_links(args, config, banco):
    saida = RAIZ / "links.html"
    saida.write_text(links.gerar_html(config), encoding="utf-8")
    print(f"Links: {saida}")


def cmd_marcar(args, config, banco):
    banco.marcar(args.chave, args.status, args.anotacao)
    cmd_relatorio(args, config, banco)


def main(argv=None):
    p = argparse.ArgumentParser(prog="imoveis", description="Busca de imóveis para alugar")
    p.add_argument("--config", default=str(RAIZ / "config.yaml"))
    p.add_argument("--banco", default=str(RAIZ / "imoveis.db"))
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("buscar")
    b.add_argument("--fontes", nargs="*", choices=list(FONTES))
    b.add_argument("--cidade", nargs="*", help="porto_alegre, nova_petropolis")
    b.set_defaults(fn=cmd_buscar)

    i = sub.add_parser("importar")
    i.add_argument("arquivo")
    i.set_defaults(fn=cmd_importar)

    sub.add_parser("relatorio").set_defaults(fn=cmd_relatorio)
    sub.add_parser("links").set_defaults(fn=cmd_links)

    m = sub.add_parser("marcar")
    m.add_argument("chave", help="código de 8 letras mostrado no cartão")
    m.add_argument("status", choices=["novo", "visto", "favorito", "visitar", "descartado"])
    m.add_argument("anotacao", nargs="?")
    m.set_defaults(fn=cmd_marcar)

    args = p.parse_args(argv)
    config = carregar_config(Path(args.config))
    args.fn(args, config, Banco(args.banco))


if __name__ == "__main__":
    main()
