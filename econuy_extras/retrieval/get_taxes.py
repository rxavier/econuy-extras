import base64
import os
import json
import re
import time
from pathlib import Path
from tempfile import NamedTemporaryFile
from datetime import datetime

import pdfplumber
import httpx
import pandas as pd
from pandas.tseries.offsets import MonthEnd
from dotenv import load_dotenv
from openai import OpenAI


load_dotenv(".env")

BASE_URL = "https://www.gub.uy/direccion-general-impositiva/datos-y-estadisticas/estadisticas?field_tematica_gubuy_to_ct_datos=563&field_fecha_by_year_to_ct_datos={}&field_fecha_by_month=All&field_publico_gubuy_to_ct_datos=All"
PROMPT = """Extract the table from the image. Return a key-value object where the keys are the taxes as defined in the first column,
and the values are the 'Variación nominal' column (NOT the 'variación real'). Do not include the % symbol with the numbers. Do not translate. Return every row.
The first element should be 'Impuestos al consumo'  and the last one 'Total neto'. Return only valid JSON that can be parsed directly. The values should be floats."""

client = OpenAI(
    api_key=os.environ["GEMINI_API_KEY"],
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)


def get_pdf_urls(dgi_year_url: str):
    try:
        r = httpx.get(dgi_year_url, timeout=60)
        r.raise_for_status()
    except httpx.HTTPStatusError as e:
        print(f"Error getting {dgi_year_url}: {e}")
        return {}

    urls = re.findall(r"files/[0-9-]+/[A-z0-9%]+\.pdf", r.text)

    if len(urls) == 0:
        return {}

    urls = {url.split("%20")[-1].replace(".pdf", ""): url for url in urls}

    months = [
        "ene",
        "feb",
        "mar",
        "abr",
        "may",
        "jun",
        "jul",
        "ago",
        "set",
        "oct",
        "nov",
        "dic",
    ]
    month_map = {m: str(i + 1).zfill(2) for i, m in enumerate(months)}

    dgi_base_url = "https://www.gub.uy/direccion-general-impositiva/sites/direccion-general-impositiva"
    final = {}
    for part, url in urls.items():
        for m, i in month_map.items():
            if m in part:
                year = "20" + url.replace(".pdf", "")[-2:]
                final[f"{year}-{i}"] = f"{dgi_base_url}/{url}"
                break
    return final


def last_page_to_image(pdf_path: str) -> str:
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[-1]
        img = page.to_image(resolution=800, antialias=True)
        with NamedTemporaryFile(suffix=".png", delete=False) as f:
            img.save(f.name, format="PNG")
    return f.name


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def parse_table(img_path: str) -> dict:
    base64_image = encode_image(img_path)
    response = client.chat.completions.create(
        model="gemini-2.0-flash",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": PROMPT,
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                    },
                ],
            }
        ],
    )
    content = response.choices[0].message.content

    data = content.strip("```json\n").replace("\\n", "\n")
    return json.loads(data)


def build_taxes_data(start_year: int = 2025):
    current_year = datetime.now().year
    if datetime.now().month == 1:
        current_year -= 1

    datas = {}
    for year in range(start_year, current_year + 1):
        url = BASE_URL.format(year)
        pdf_urls = get_pdf_urls(url)

        if not pdf_urls:
            print(f"No PDFs found for year {year}")
            continue

        for year_month, pdf_url in pdf_urls.items():
            print(f"Processing month {year_month}")
            r = httpx.get(pdf_url)
            with NamedTemporaryFile(suffix=".pdf", delete=True) as f:
                f.write(r.content)
                img_path = last_page_to_image(f.name)

                try:
                    data = parse_table(img_path)
                except Exception as exc:
                    print(f"Failure on {year_month=} {pdf_url=} | {exc}")
                    time.sleep(60)
                    data = parse_table(img_path)

                datas[year_month] = data

    output = pd.DataFrame(datas).T
    output.index = pd.to_datetime(output.index, format="%Y-%m")
    output.index = output.index + MonthEnd()
    output = output.sort_index()
    cols = [
        "IVA",
        "IMESI",
        "IMEBA",
        "IRAE",
        "Categoría I",
        "Categoría II",
        "IASS",
        "IRNR",
        "Impuesto de Primaria",
        "Total Bruto (suma de (1) a (5))",
    ]
    output = output[cols]
    output_path = Path(__file__).parent / "taxes_pdf.csv"
    output.to_csv(output_path)
    return output


if __name__ == "__main__":
    build_taxes_data()
