import json
import subprocess
import sys
from pathlib import Path

import pytest
from openpyxl import load_workbook

import ornek_veri_uret
from rapor.cli import main

KOK = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def rapor(tmp_path_factory):
    klasor = tmp_path_factory.mktemp("veri")
    beklenen = ornek_veri_uret.uret(klasor)
    cikti = klasor / "rapor.xlsx"  # çıktı girdi klasöründe olsa bile girdi sayılmamalı
    assert main([str(klasor), "--cikti", str(cikti)]) == 0
    return beklenen, load_workbook(str(cikti))


def test_sayfalar(rapor):
    _, wb = rapor
    assert wb.sheetnames == ["Özet", "Aylık", "Tüm Kayıtlar", "Atılan Satırlar"]


def test_toplamlar_uretecin_dogru_toplamiyla_eslesir(rapor):
    beklenen, wb = rapor
    ozet = wb["Özet"]
    assert ozet["A4"].value == "Toplam ciro"
    assert ozet["B4"].value == pytest.approx(beklenen["toplam_ciro"], abs=0.005)
    assert ozet["B5"].value == beklenen["siparis_sayisi"]
    kayitlar = wb["Tüm Kayıtlar"]
    assert kayitlar.max_row - 1 == beklenen["satir_sayisi"]
    assert sum(r[5] for r in kayitlar.iter_rows(min_row=2, values_only=True)) == \
        pytest.approx(beklenen["toplam_ciro"], abs=0.005)


def test_sube_ve_ay_dokumu(rapor):
    beklenen, wb = rapor
    aylik = wb["Aylık"]
    satirlar = {r[0]: r for r in aylik.iter_rows(min_row=2, values_only=True)}
    for sube, ciro in beklenen["sube_ciro"].items():
        assert satirlar[sube][-1] == pytest.approx(ciro, abs=0.005)
    ay_toplamlari = satirlar["Toplam"][1:-1]
    assert ay_toplamlari == pytest.approx(list(beklenen["ay_ciro"].values()), abs=0.005)


def test_atilanlar_listelenir_nedenleriyle(rapor):
    beklenen, wb = rapor
    atilan = list(wb["Atılan Satırlar"].iter_rows(min_row=2, values_only=True))
    assert len(atilan) == beklenen["yinelenen"] + beklenen["bozuk"]
    nedenler = [r[2] for r in atilan]
    assert sum(n.startswith("Yinelenen") for n in nedenler) == beklenen["yinelenen"]
    assert sum(n.startswith("Bozuk") for n in nedenler) == beklenen["bozuk"]


def test_ozette_grafik_ve_bicimler_var(rapor):
    _, wb = rapor
    assert len(wb["Özet"]._charts) == 1
    k = wb["Tüm Kayıtlar"]
    assert k.freeze_panes == "A2" and k.auto_filter.ref
    assert "TL" in k["F2"].number_format and k["A2"].number_format == "dd.mm.yyyy"


def test_komut_satiri_ozeti_ve_hatalari(tmp_path):
    veri = tmp_path / "v"
    ornek_veri_uret.uret(veri)
    cikti = tmp_path / "r.xlsx"
    p = subprocess.run([sys.executable, "-m", "rapor", str(veri), "--cikti", str(cikti)],
                       cwd=str(KOK), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       universal_newlines=True)
    assert p.returncode == 0 and cikti.exists()
    assert "Okunan dosya     : 9" in p.stdout and "Çıktı" in p.stdout
    p = subprocess.run([sys.executable, "-m", "rapor", str(tmp_path / "yok")],
                       cwd=str(KOK), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       universal_newlines=True)
    assert p.returncode == 1 and "Klasör bulunamadı" in p.stderr


def test_tanimayan_sutun_mesaji(tmp_path, capsys):
    (tmp_path / "Konak_x.csv").write_text("Tarih;Ürün;Kazanç\n01.08.2026;Termos;5\n", encoding="utf-8")
    assert main([str(tmp_path), "--cikti", str(tmp_path / "o.xlsx")]) == 1
    hata = capsys.readouterr().err
    assert "Konak_x.csv" in hata and "tutar" in hata and "Kazanç" in hata


def test_uretici_tekrarlanabilir(tmp_path):
    a = ornek_veri_uret.uret(tmp_path / "a")
    b = ornek_veri_uret.uret(tmp_path / "b")
    assert a == b
    assert json.loads((tmp_path / "a" / "beklenen.json").read_text(encoding="utf-8")) == a
