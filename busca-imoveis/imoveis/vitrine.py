"""Gera vitrine.html: página única para celular, com fotos embutidas, pronta para publicar e compartilhar.

As fotos ficam embutidas (data URI) porque a página publicada não pode carregar imagens de outros sites.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
from datetime import datetime
from pathlib import Path

import requests

try:
    from PIL import Image
except ImportError:  # sem Pillow, as fotos vão no tamanho original
    Image = None

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"


def _foto(url: str, cache: Path) -> str | None:
    cache.mkdir(parents=True, exist_ok=True)
    arq = cache / (hashlib.sha1(url.encode()).hexdigest() + ".jpg")
    if not arq.exists():
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=25)
            r.raise_for_status()
            dados = r.content
            if Image:
                im = Image.open(io.BytesIO(dados)).convert("RGB")
                im.thumbnail((640, 640))
                buf = io.BytesIO()
                im.save(buf, "JPEG", quality=66, optimize=True, progressive=True)
                dados = buf.getvalue()
            arq.write_bytes(dados)
        except Exception:  # noqa: BLE001
            return None
    return "data:image/jpeg;base64," + base64.b64encode(arq.read_bytes()).decode()


def montar_dados(linhas: list[dict], config: dict, cache: Path, fotos_por_imovel: int = 4) -> list[dict]:
    saida = []
    for l in linhas:
        d, a = l["dados"], l["avaliacao"]
        fotos = [f for f in (_foto(u, cache) for u in d.get("fotos", [])[:fotos_por_imovel]) if f]
        saida.append({
            "id": l["chave"][:8], "nota": round(l["nota"]), "fonte": d["fonte"], "url": d["url"],
            "bairro": d.get("bairro", ""), "endereco": d.get("endereco", ""), "titulo": d.get("titulo", ""),
            "area": d.get("area"), "quartos": d.get("quartos"), "vagas": d.get("vagas"), "pet": d.get("pet"),
            "aluguel": d.get("aluguel"), "condominio": d.get("condominio"), "iptu": d.get("iptu_mensal"),
            "cond_iptu": d.get("condominio_inclui_iptu", False), "total": d.get("total"),
            "lat": d.get("lat"), "lon": d.get("lon"), "quadras": a.get("quadras"), "km": a.get("distancia_km"),
            "destaques": a.get("destaques", []), "alertas": a.get("alertas", []),
            "acima": a.get("acima_do_teto", False), "fotos": fotos,
        })
    return saida


def gerar_html(itens: list[dict], config: dict) -> str:
    ref = config["referencia"]
    meta = {
        "ref": {"lat": ref["lat"], "lon": ref["lon"], "nome": ref["nome"], "mq": ref.get("metros_por_quadra", 110)},
        "teto": config["orcamento"]["maximo"], "teto_flex": config["orcamento"]["teto_flexivel_poa"],
        "data": datetime.now().strftime("%d/%m/%Y"),
    }
    modelo = (Path(__file__).parent / "vitrine_modelo.html").read_text(encoding="utf-8")
    dados = json.dumps({"meta": meta, "itens": itens}, ensure_ascii=False).replace("</", "<\\/")
    return modelo.replace("/*__DADOS__*/null", dados)
