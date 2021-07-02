import datetime as dt
import warnings
import re
import sys
from tempfile import NamedTemporaryFile

import pandas as pd
import requests
import camelot
from PyPDF2 import pdf as pdf2
from PyPDF2.utils import PdfReadWarning


def get_taxes_from_pdf(start_year: int = 2020) -> pd.DataFrame:
    base_url = "https://www.dgi.gub.uy/wdgi/page?2,principal,dgi--datos-y-series-estadisticas--informes-mensuales-de-la-recaudacion-"
    extra_url = ",O,es,0,"
    reports_year = range(start_year, dt.date.today().year + 1)
    data = []
    for year in reports_year:
        url = f"{base_url}{year}{extra_url}"
        r = requests.get(url)
        pdf_urls = re.findall("afiledownload\?2,4,[0-9]{4},O,S,0,[0-9]+"
                              "%[0-9A-z]{3}%[0-9A-z]{3}%3B108,", r.text)
        pdf_urls = list(dict.fromkeys(pdf_urls))
        if len(pdf_urls) == 0:
            continue
        dates = pd.date_range(start=dt.datetime(year, 1, 1), freq="M",
                              periods=len(pdf_urls))
        if sys.platform == "win32":
            delete = False
        else:
            delete = True
        for pdf, date in zip(pdf_urls, dates):
            with NamedTemporaryFile(suffix=".pdf", delete=delete) as f:
                r = requests.get(f"https://www.dgi.gub.uy/wdgi/{pdf}")
                f.write(r.content)
                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore", category=PdfReadWarning)
                    pages = pdf2.PdfFileReader(f.name).getNumPages()
                tables = camelot.read_pdf(f.name, flavor="stream",
                                          pages=str(pages), strip_text="%")
                table = tables[0].df.iloc[2:, [0, 3]]
                table.columns = ["Impuesto", date]
                table.set_index("Impuesto", inplace=True)
                table[date] = table[date].str.replace(",", ".", regex=False)
                table = (table.apply(pd.to_numeric, errors="coerce")
                         .dropna(how="any").T)
                table = table.loc[:,
                                  ["IVA",
                                   "IMESI",
                                   "IMEBA",
                                   "IRAE",
                                   "Categoría I",
                                   "Categoría II",
                                   "IASS",
                                   "IRNR",
                                   "Impuesto de Primaria",
                                   "6) Total Bruto (suma de (1) a (5))"]]
                # The may-21 table had hidden duplicate rows with different values
                # See https://www.dgi.gub.uy/wdgi/afiledownload?2,4,1879,O,S,0,36556%3BS%3B1%3B108,
                if table.shape[1] == 20:
                    table = table.iloc[:, 0:table.shape[1]:2]
                table.columns = [
                    'IVA - Valor Agregado',
                    'IMESI - Específico Interno',
                    'IMEBA - Enajenación de Bienes Agropecuarios',
                    'IRAE - Rentas de Actividades Económicas',
                    'IRPF Cat I - Renta de las Personas Físicas',
                    'IRPF Cat II - Rentas de las Personas Físicas',
                    'IASS - Asistencia a la Seguridad Social',
                    'IRNR - Rentas de No Residentes',
                    'Impuesto de Educación Primaria',
                    'Recaudación Total de la DGI']
                data.append(table)
    output = pd.concat(data)
    output.to_csv("econuy_extras/retrieval/taxes.csv")

    return output

if __name__=="__main__":
    get_taxes_from_pdf()
