"""Temizlenmiş veriden biçimlendirilmiş Excel raporu yazar."""
from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

AYLAR_TR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz",
            "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
TL = '#,##0.00 "TL"'
TARIH = "dd.mm.yyyy"
YUZDE = "0.0%"

RENK = "1F5F5B"
BASLIK_DOLGU = PatternFill("solid", fgColor=RENK)
BASLIK_YAZI = Font(name="Calibri", bold=True, color="FFFFFF")
TOPLAM_DOLGU = PatternFill("solid", fgColor="E4EFEE")
YAZI = Font(name="Calibri", size=11)
KALIN = Font(name="Calibri", size=11, bold=True)
ALT_CIZGI = Border(bottom=Side(style="thin", color="D0D7D6"))


def ay_etiketi(yil, ay):
    return "{} {}".format(AYLAR_TR[ay - 1], yil)


def _baslik_satiri(ws, satir, basliklar, ilk_sutun=1, sag=True):
    for j, b in enumerate(basliklar):
        h = ws.cell(row=satir, column=ilk_sutun + j, value=b)
        h.font, h.fill = BASLIK_YAZI, BASLIK_DOLGU
        h.alignment = Alignment(horizontal="left" if j == 0 else ("right" if sag else "center"),
                                vertical="center", wrap_text=True)


def _genislikler(ws, genislikler):
    for i, g in enumerate(genislikler, start=1):
        ws.column_dimensions[get_column_letter(i)].width = g


def _bolum(ws, satir, metin):
    c = ws.cell(row=satir, column=1, value=metin)
    c.font = Font(name="Calibri", size=13, bold=True, color=RENK)


def _grupla(df, anahtar):
    """anahtar -> (sipariş sayısı, adet, ciro) ; anahtar sırasına göre."""
    g = df.groupby(anahtar, sort=True)
    return [(k, d["siparis_anahtar"].nunique(), int(d["adet"].sum()),
             round(float(d["tutar"].sum()), 2)) for k, d in g]


def _ozet_sayfasi(ws, df, istatistik):
    ws.sheet_view.showGridLines = False
    ciro = round(float(df["tutar"].sum()), 2)
    siparis = df["siparis_anahtar"].nunique()
    ws["A1"] = "Satış Raporu"
    ws["A1"].font = Font(name="Calibri", size=18, bold=True, color=RENK)
    ws["A2"] = "Dönem: {:%d.%m.%Y} – {:%d.%m.%Y}  ·  {} dosya  ·  {} kayıt".format(
        df["tarih"].min(), df["tarih"].max(), istatistik["dosya"], len(df))
    ws["A2"].font = Font(name="Calibri", size=10, color="666666")

    for satir, (etiket, deger, bicim) in enumerate([
            ("Toplam ciro", ciro, TL), ("Sipariş sayısı", siparis, "#,##0"),
            ("Ortalama sipariş tutarı", round(ciro / siparis, 2), TL)], start=4):
        ws.cell(row=satir, column=1, value=etiket).font = YAZI
        c = ws.cell(row=satir, column=2, value=deger)
        c.font, c.number_format = Font(name="Calibri", size=12, bold=True), bicim
        c.alignment = Alignment(horizontal="right")

    def tablo(baslangic, baslik, ilk, satirlar, toplam=True):
        _bolum(ws, baslangic, baslik)
        _baslik_satiri(ws, baslangic + 1, [ilk, "Sipariş", "Ciro", "Pay"])
        r = baslangic + 2
        for etiket, sip, _, c in satirlar:
            ws.cell(row=r, column=1, value=etiket)
            ws.cell(row=r, column=2, value=sip).number_format = "#,##0"
            ws.cell(row=r, column=3, value=c).number_format = TL
            ws.cell(row=r, column=4, value=c / ciro).number_format = YUZDE
            for j in range(1, 5):
                ws.cell(row=r, column=j).border = ALT_CIZGI
                ws.cell(row=r, column=j).font = YAZI
            r += 1
        if toplam:
            ws.cell(row=r, column=1, value="Toplam")
            ws.cell(row=r, column=2, value=siparis).number_format = "#,##0"
            ws.cell(row=r, column=3, value=ciro).number_format = TL
            ws.cell(row=r, column=4, value=1).number_format = YUZDE
            for j in range(1, 5):
                ws.cell(row=r, column=j).font = KALIN
                ws.cell(row=r, column=j).fill = TOPLAM_DOLGU
            r += 1
        return r

    sonraki = tablo(9, "Şube bazında", "Şube", _grupla(df, "sube"))
    ay_baslangic = sonraki + 1
    aylar = _grupla(df.assign(ay=[(d.year, d.month) for d in df["tarih"]]), "ay")
    aylar = [(ay_etiketi(*k), s, a, c) for k, s, a, c in aylar]
    sonraki = tablo(ay_baslangic, "Ay bazında", "Ay", aylar)

    # En çok satan 10 ürün (ciroya göre)
    urun_baslangic = sonraki + 1
    _bolum(ws, urun_baslangic, "En çok satan 10 ürün (ciroya göre)")
    _baslik_satiri(ws, urun_baslangic + 1, ["Ürün", "Adet", "Ciro", "Pay"])
    ilk10 = sorted(_grupla(df, "urun"), key=lambda x: (-x[3], x[0]))[:10]
    for i, (ad, _, adet, c) in enumerate(ilk10):
        r = urun_baslangic + 2 + i
        ws.cell(row=r, column=1, value=ad)
        ws.cell(row=r, column=2, value=adet).number_format = "#,##0"
        ws.cell(row=r, column=3, value=c).number_format = TL
        ws.cell(row=r, column=4, value=c / ciro).number_format = YUZDE
        for j in range(1, 5):
            ws.cell(row=r, column=j).border = ALT_CIZGI
            ws.cell(row=r, column=j).font = YAZI
    _genislikler(ws, [30, 20, 18, 10, 3])

    # Aylık ciro grafiği: ay tablosunun Ciro sütunundan beslenir.
    ilk_ay_satiri = ay_baslangic + 2
    son_ay_satiri = ilk_ay_satiri + len(aylar) - 1
    grafik = BarChart()
    grafik.type = "col"
    grafik.title = "Aylık ciro (TL)"
    grafik.legend = None
    grafik.add_data(Reference(ws, min_col=3, min_row=ilk_ay_satiri - 1,
                              max_row=son_ay_satiri), titles_from_data=True)
    grafik.set_categories(Reference(ws, min_col=1, min_row=ilk_ay_satiri,
                                    max_row=son_ay_satiri))
    grafik.series[0].graphicalProperties.solidFill = RENK
    grafik.y_axis.numFmt = "#,##0"
    grafik.y_axis.scaling.min = 0  # eksen sıfırdan başlasın, fark abartılmasın
    grafik.x_axis.delete = False
    grafik.y_axis.delete = False
    grafik.gapWidth = 60
    grafik.width, grafik.height = 17, 9
    ws.add_chart(grafik, "F4")


def _aylik_sayfasi(ws, df):
    df = df.assign(ay=[(d.year, d.month) for d in df["tarih"]])
    aylar = sorted(set(df["ay"]))
    subeler = sorted(set(df["sube"]))
    _baslik_satiri(ws, 1, ["Şube"] + [ay_etiketi(*a) for a in aylar] + ["Toplam"])
    pivot = df.groupby(["sube", "ay"])["tutar"].sum()
    for i, s in enumerate(subeler, start=2):
        ws.cell(row=i, column=1, value=s)
        satir_toplam = 0.0
        for j, a in enumerate(aylar, start=2):
            v = round(float(pivot.get((s, a), 0.0)), 2)
            satir_toplam += v
            ws.cell(row=i, column=j, value=v).number_format = TL
        ws.cell(row=i, column=len(aylar) + 2, value=round(satir_toplam, 2)).number_format = TL
        for j in range(1, len(aylar) + 3):
            ws.cell(row=i, column=j).font = KALIN if j == len(aylar) + 2 else YAZI
            ws.cell(row=i, column=j).border = ALT_CIZGI
    t = len(subeler) + 2
    ws.cell(row=t, column=1, value="Toplam")
    for j, a in enumerate(aylar, start=2):
        ws.cell(row=t, column=j, value=round(float(df.loc[df["ay"] == a, "tutar"].sum()), 2))
    ws.cell(row=t, column=len(aylar) + 2, value=round(float(df["tutar"].sum()), 2))
    for j in range(1, len(aylar) + 3):
        c = ws.cell(row=t, column=j)
        c.font, c.fill = KALIN, TOPLAM_DOLGU
        if j > 1:
            c.number_format = TL
    _genislikler(ws, [18] + [18] * (len(aylar) + 1))
    ws.freeze_panes = "B2"


def _kayitlar_sayfasi(ws, df):
    basliklar = ["Tarih", "Şube", "Sipariş No", "Ürün", "Adet", "Tutar", "Kaynak Dosya"]
    _baslik_satiri(ws, 1, basliklar, sag=False)
    for i, r in enumerate(df.itertuples(index=False), start=2):
        ws.cell(row=i, column=1, value=r.tarih).number_format = TARIH
        ws.cell(row=i, column=2, value=r.sube)
        ws.cell(row=i, column=3, value=r.siparis_no or None)
        ws.cell(row=i, column=4, value=r.urun)
        ws.cell(row=i, column=5, value=int(r.adet))
        ws.cell(row=i, column=6, value=float(r.tutar)).number_format = TL
        ws.cell(row=i, column=7, value=r.kaynak)
        ws.cell(row=i, column=1).alignment = Alignment(horizontal="center")
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = "A1:{}{}".format(get_column_letter(len(basliklar)), len(df) + 1)
    _genislikler(ws, [12, 14, 14, 26, 8, 16, 26])


def _atilan_sayfasi(ws, atilan):
    basliklar = ["Kaynak Dosya", "Satır No", "Neden Atıldı", "Satırın İçeriği"]
    _baslik_satiri(ws, 1, basliklar, sag=False)
    if atilan.empty:
        ws.cell(row=2, column=1, value="Atılan satır yok.")
    for i, r in enumerate(atilan.itertuples(index=False), start=2):
        ws.cell(row=i, column=1, value=r.kaynak)
        ws.cell(row=i, column=2, value=int(r.satir_no)).alignment = Alignment(horizontal="center")
        ws.cell(row=i, column=3, value=r.neden)
        ws.cell(row=i, column=4, value=r.icerik)
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = "A1:D{}".format(max(len(atilan) + 1, 2))
    _genislikler(ws, [26, 10, 62, 60])


def rapor_yaz(yol, df, atilan, istatistik):
    wb = Workbook()
    ws = wb.active
    ws.title = "Özet"
    _ozet_sayfasi(ws, df, istatistik)
    _aylik_sayfasi(wb.create_sheet("Aylık"), df)
    _kayitlar_sayfasi(wb.create_sheet("Tüm Kayıtlar"), df)
    _atilan_sayfasi(wb.create_sheet("Atılan Satırlar"), atilan)
    for sayfa in wb.worksheets:
        sayfa.sheet_properties.tabColor = RENK
        sayfa.page_setup.orientation = "landscape"  # yazdırırken tek sayfa genişliği
        sayfa.page_setup.fitToWidth = 1
        sayfa.page_setup.fitToHeight = 0
        sayfa.sheet_properties.pageSetUpPr.fitToPage = True
    wb.save(str(yol))
