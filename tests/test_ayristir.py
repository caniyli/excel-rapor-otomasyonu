import datetime as dt

import pytest

from rapor.ayristir import (adet_ayristir, metin_temizle, tarih_ayristir,
                            tutar_ayristir)


@pytest.mark.parametrize("ham, beklenen", [
    ("1.234,50", 1234.50),
    ("1234,5", 1234.5),
    ("12,5", 12.5),
    ("1.250", 1250.0),          # tek nokta + 3 hane: binlik
    ("12.345.678,90", 12345678.90),
    ("12.5", 12.5),             # nokta + 2 hane: ondalık
    ("1,234.50", 1234.50),      # İngilizce biçim de okunur
    ("1.375,00 TL", 1375.0),
    ("₺ 99,90", 99.90),
    ("  640 ", 640.0),
    ("-45,25", -45.25),
    (1050, 1050.0),
    (199.9, 199.9),
])
def test_tutar_ayristir(ham, beklenen):
    assert tutar_ayristir(ham) == pytest.approx(beklenen)


@pytest.mark.parametrize("ham", ["belirsiz", "", None, "#DEĞER!", "-", "1,2,3x", True, float("nan")])
def test_tutar_okunamayan(ham):
    with pytest.raises(ValueError):
        tutar_ayristir(ham)


def test_adet():
    assert adet_ayristir("3") == 3
    assert adet_ayristir(4.0) == 4
    for kotu in ("0", "-1", "2,5", "iki"):
        with pytest.raises(ValueError):
            adet_ayristir(kotu)


@pytest.mark.parametrize("ham, beklenen", [
    ("24.11.2026", dt.date(2026, 11, 24)),
    ("2026-11-24", dt.date(2026, 11, 24)),
    ("24/11/2026", dt.date(2026, 11, 24)),
    ("03.09.2026", dt.date(2026, 9, 3)),   # gün-ay-yıl: 3 Eylül
    ("5.1.2026", dt.date(2026, 1, 5)),
    ("2026-11-24 00:00:00", dt.date(2026, 11, 24)),
    (dt.datetime(2026, 11, 24, 13, 0), dt.date(2026, 11, 24)),
    (dt.date(2026, 11, 24), dt.date(2026, 11, 24)),
])
def test_tarih_ayristir(ham, beklenen):
    assert tarih_ayristir(ham) == beklenen


@pytest.mark.parametrize("ham", ["31.02.2026", "yarın", "", None, "24.11.26", "2026-13-01"])
def test_tarih_okunamayan(ham):
    with pytest.raises(ValueError):
        tarih_ayristir(ham)


def test_metin_temizle():
    assert metin_temizle("  Çay   Demlik \xa0Seti ") == "Çay Demlik Seti"
    assert metin_temizle(None) == ""
    assert metin_temizle(float("nan")) == ""
