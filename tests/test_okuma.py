import pytest

from rapor.hatalar import RaporHatasi
from rapor.okuma import ayrac_algila, dosyalari_bul, kodlama_algila, oku

METIN = "Tarih;Ürün;Tutar\n24.11.2026;Çay Demlik Seti;1.250,00\n"


def test_kodlama_algila():
    assert kodlama_algila(METIN.encode("utf-8")) == "utf-8"
    assert kodlama_algila(METIN.encode("utf-8-sig")) == "utf-8-sig"
    assert kodlama_algila(METIN.encode("cp1254")) == "cp1254"
    assert kodlama_algila(b"Tarih;Urun") == "utf-8"


@pytest.mark.parametrize("ayrac", [";", ",", "\t", "|"])
def test_ayrac_algila(ayrac):
    assert ayrac_algila(ayrac.join(["Tarih", "Ürün", "Tutar"]) + "\n1,2,3") == ayrac


@pytest.mark.parametrize("kodlama", ["utf-8", "utf-8-sig", "cp1254"])
def test_csv_turkce_karakterler_dogru_okunur(tmp_path, kodlama):
    yol = tmp_path / "Konak_2026-08.csv"
    yol.write_bytes(METIN.encode(kodlama))
    t = oku(yol)
    assert t.basliklar == ["Tarih", "Ürün", "Tutar"]
    assert t.satirlar == [(2, ["24.11.2026", "Çay Demlik Seti", "1.250,00"])]


def test_klasor_taramasi(tmp_path):
    for ad in ("b.csv", "a.xlsx", "~$a.xlsx", ".gizli.csv", "not.txt"):
        (tmp_path / ad).write_text("x")
    assert [p.name for p in dosyalari_bul(tmp_path)] == ["a.xlsx", "b.csv"]
    assert [p.name for p in dosyalari_bul(tmp_path, haric=tmp_path / "b.csv")] == ["a.xlsx"]


def test_klasor_yok_ya_da_bos(tmp_path):
    with pytest.raises(RaporHatasi, match="bulunamadı"):
        dosyalari_bul(tmp_path / "yok")
    with pytest.raises(RaporHatasi, match="yok"):
        dosyalari_bul(tmp_path)
