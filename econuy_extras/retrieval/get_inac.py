import httpx
from pathlib import Path

FAENA_URL = "https://www.inac.uy/innovaportal/file/11998/1/evolucion-semanal-faena-bovinos-y-ovinos.xlsx"
PRECIOS_URL = "https://www.inac.uy/innovaportal/file/9799/1/evolucion-semanal-exportacion_total-sector-carnico.xlsx"

def download_inac_files():
    """Download weekly slaughter and price data from INAC."""
    output_dir = Path(__file__).parent

    # Download faena (slaughter) data
    try:
        r = httpx.get(FAENA_URL)
        r.raise_for_status()
        with open(output_dir / "faena.xlsx", "wb") as f:
            f.write(r.content)
        print("Successfully downloaded faena.xlsx")
    except httpx.HTTPStatusError as e:
        print(f"Error downloading faena data: {e}")

    # Download export prices data
    try:
        r = httpx.get(PRECIOS_URL)
        r.raise_for_status()
        with open(output_dir / "precios.xlsx", "wb") as f:
            f.write(r.content)
        print("Successfully downloaded precios.xlsx")
    except httpx.HTTPStatusError as e:
        print(f"Error downloading precios data: {e}")

if __name__ == "__main__":
    download_inac_files()
