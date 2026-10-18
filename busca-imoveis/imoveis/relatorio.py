"""Gera relatorio.html: cartões ordenados pela nota, com filtros por cidade e status."""
from __future__ import annotations

from datetime import datetime
from html import escape


def _brl(v) -> str:
    return "—" if v is None else "R$ " + f"{v:,.0f}".replace(",", ".")


def _cartao(l: dict) -> str:
    d, a = l["dados"], l["avaliacao"]
    tags = "".join(f'<span class="tag ok">{escape(t)}</span>' for t in a["destaques"])
    tags += "".join(f'<span class="tag alerta">{escape(t)}</span>' for t in a["alertas"])
    foto = f'<img src="{escape(d["fotos"][0])}" loading="lazy" alt="">' if d.get("fotos") else ""
    dist = f' · {a["distancia_km"]} km da Soledade' if a.get("distancia_km") is not None else ""
    novo = '<span class="novo">NOVO</span>' if l["status"] == "novo" else ""
    info = " · ".join(x for x in [
        f'{d["area"]:.0f} m²' if d.get("area") else "",
        f'{d["quartos"]} quartos' if d.get("quartos") else "",
        f'{d["vagas"]} vaga(s)' if d.get("vagas") else "",
        d.get("tipo", ""),
    ] if x)
    return f"""
<article class="card" data-cidade="{escape(d['cidade'])}" data-status="{escape(l['status'])}">
  {foto}
  <div class="corpo">
    <div class="topo"><span class="nota">{l['nota']:.0f}</span>{novo}
      <span class="bairro">{escape(d['bairro'])} — {escape(d['cidade'])}</span></div>
    <div class="preco"><b>{_brl(d.get('total'))}</b>/mês
      <small>(aluguel {_brl(d.get('aluguel'))} + cond. {_brl(d.get('condominio'))}; IPTU {_brl(d.get('iptu_mensal'))})</small></div>
    <div>{escape(info)}{escape(dist)}</div>
    <div class="titulo">{escape(d.get('titulo') or d.get('endereco') or '')}</div>
    <div>{tags}</div>
    <div class="rodape"><a href="{escape(d['url'])}" target="_blank" rel="noopener">Abrir anúncio ({escape(d['fonte'])})</a>
      <code>{l['chave'][:8]}</code> <i>{escape(l['status'])}</i> {escape(l.get('anotacao') or '')}</div>
  </div>
</article>"""


def gerar_html(linhas: list[dict]) -> str:
    cidades = sorted({l["dados"]["cidade"] for l in linhas})
    botoes = "".join(f'<button data-f="{escape(c)}">{escape(c)}</button>' for c in cidades)
    cartoes = "".join(_cartao(l) for l in linhas) or "<p>Nenhum imóvel aprovado ainda. Rode <code>python -m imoveis buscar</code>.</p>"
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Imóveis para alugar</title>
<style>
:root{{--bg:#f6f5f2;--card:#fff;--tx:#222;--mut:#666;--ok:#e3f4e8;--okt:#1d6b35;--al:#fff1db;--alt:#8a5300;--ac:#0b5cad}}
@media (prefers-color-scheme:dark){{:root{{--bg:#16171a;--card:#212328;--tx:#eee;--mut:#aaa;--ok:#1f3a28;--okt:#9be0b0;--al:#3d2e14;--alt:#f3c27a;--ac:#7db7ff}}}}
body{{margin:0;background:var(--bg);color:var(--tx);font-family:system-ui,sans-serif}}
header{{padding:16px;max-width:1100px;margin:auto}} main{{display:grid;gap:16px;padding:0 16px 32px;max-width:1100px;margin:auto;
grid-template-columns:repeat(auto-fill,minmax(300px,1fr))}}
.card{{background:var(--card);border-radius:12px;overflow:hidden;box-shadow:0 1px 3px #0002}}
.card img{{width:100%;height:180px;object-fit:cover}} .corpo{{padding:12px;display:grid;gap:6px}}
.nota{{background:var(--ac);color:#fff;border-radius:8px;padding:2px 8px;font-weight:700;margin-right:6px}}
.novo{{background:#d33;color:#fff;border-radius:6px;padding:1px 6px;font-size:12px;margin-right:6px}}
.bairro{{font-weight:600}} .preco small,.rodape code,.rodape i{{color:var(--mut)}} .titulo{{color:var(--mut);font-size:14px}}
.tag{{display:inline-block;font-size:12px;border-radius:999px;padding:2px 8px;margin:2px 4px 0 0}}
.ok{{background:var(--ok);color:var(--okt)}} .alerta{{background:var(--al);color:var(--alt)}}
a{{color:var(--ac)}} button{{margin:4px;padding:6px 12px;border-radius:999px;border:1px solid var(--mut);background:var(--card);color:var(--tx)}}
button.ativo{{background:var(--ac);color:#fff;border-color:var(--ac)}}
</style></head><body>
<header><h1>Imóveis para alugar</h1>
<p>{len(linhas)} aprovados · atualizado em {datetime.now():%d/%m/%Y %H:%M}. Nota de 0 a 100 (bairro, distância da Soledade, segurança, estado, espaço, lazer, preço).</p>
<div><button data-f="" class="ativo">Todos</button>{botoes}<button data-s="novo">Só novos</button><button data-s="favorito">Favoritos</button></div>
</header><main>{cartoes}</main>
<script>
let fc="",fs="";
document.querySelectorAll("button").forEach(b=>b.onclick=()=>{{
 if(b.dataset.f!==undefined){{fc=b.dataset.f;fs="";}} else fs=(fs===b.dataset.s?"":b.dataset.s);
 document.querySelectorAll("button").forEach(x=>x.classList.toggle("ativo",(x.dataset.f!==undefined&&x.dataset.f===fc&&!fs)||(x.dataset.s&&x.dataset.s===fs)));
 document.querySelectorAll(".card").forEach(c=>c.style.display=((!fc||c.dataset.cidade===fc)&&(!fs||c.dataset.status===fs))?"":"none");
}});
</script></body></html>"""
