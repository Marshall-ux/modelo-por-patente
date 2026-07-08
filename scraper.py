"""Lógica de scraping compartida para consultar deuda de patentes en el portal
de la Provincia de Santa Fe (https://www.santafe.gov.ar/e-pt-liq-deuda/).

Usa Playwright (Chromium headless) para completar el formulario, resolver el
captcha Altcha (proof-of-work) y extraer los datos del vehículo, avisos y las
tablas de deuda. Devuelve siempre un diccionario con la clave "success".

Tanto la app web (app.py) como la CLI (cli.py) usan `consultar_patente_data`.
"""

import re

from playwright.async_api import async_playwright

PORTAL_URL = "https://www.santafe.gov.ar/e-pt-liq-deuda/"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def normalizar_patente(patente: str) -> str:
    """Limpia la patente: mayúsculas, sin espacios ni guiones."""
    return patente.strip().upper().replace(" ", "").replace("-", "")


async def consultar_patente_data(patente: str, headless: bool = True) -> dict:
    """Consulta la deuda de una patente y devuelve los datos estructurados.

    Retorna un dict con:
      - success: bool
      - si success es False: error (str)
      - si success es True: vehicle_data (list[str]), notices (list[str]),
        debts (list[{"headers": [...], "rows": [[...]]}])
    """
    patente = normalizar_patente(patente)
    if not patente:
        return {"success": False, "error": "La patente ingresada está vacía."}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(user_agent=USER_AGENT)
        page = await context.new_page()

        try:
            await page.goto(PORTAL_URL, timeout=30000)

            # Completar la patente
            await page.wait_for_selector("#nupatente", timeout=15000)
            await page.fill("#nupatente", patente)

            # Marcar checkbox del captcha Altcha
            checkbox_selector = 'altcha-widget input[type="checkbox"]'
            await page.wait_for_selector(checkbox_selector, timeout=10000)
            await page.click(checkbox_selector)

            # Esperar la verificación proof-of-work
            await page.wait_for_selector(
                'altcha-widget .altcha[data-state="verified"]', timeout=15000
            )

            # Enviar el formulario
            await page.click('input[name="Aceptar"]')
            await page.wait_for_load_state("domcontentloaded")

            # Si seguimos en la página de entrada, hubo un error de validación
            is_input_page = await page.locator("#nupatente").count() > 0
            if is_input_page:
                error_selector = ".ui-state-error"
                if await page.locator(error_selector).count() > 0:
                    error_locators = await page.locator(error_selector).all()
                    error_texts = []
                    for loc in error_locators:
                        txt = await loc.inner_text()
                        error_texts.append(txt.replace("\n", " ").strip())
                    error_clean = re.sub(r"\s+", " ", " | ".join(error_texts))
                    return {"success": False, "error": error_clean}

                body_text = await page.inner_text("body")
                if "DOMINIO INEXISTENTE" in body_text:
                    return {"success": False, "error": "Dominio inexistente."}
                return {
                    "success": False,
                    "error": "Error de validación desconocido en el portal.",
                }

            # Extraer datos del vehículo
            vehicle_data = []
            labels = await page.locator(".form-label label").all()
            for label in labels:
                text = re.sub(r"\s+", " ", await label.inner_text()).strip()
                if text:
                    text = text.replace(" :", ":").replace(" - ", " | ")
                    vehicle_data.append(text)

            # Extraer avisos / notas (exenciones, al día, etc.)
            notices = []
            notice_elements = await page.locator(".ui-state-error").all()
            for el in notice_elements:
                txt = re.sub(r"\s+", " ", await el.inner_text()).strip()
                if txt and txt not in notices:
                    notices.append(txt)

            # Extraer tablas de deuda
            debts = []
            tables = await page.locator("table").all()
            for table in tables:
                headers = []
                for th in await table.locator("th").all():
                    headers.append((await th.inner_text()).strip())

                rows_data = []
                for tr in await table.locator("tr").all():
                    if await tr.locator("th").count() > 0:
                        continue
                    row_cells = []
                    for td in await tr.locator("td").all():
                        row_cells.append((await td.inner_text()).strip())
                    if row_cells:
                        rows_data.append(row_cells)

                if rows_data:
                    if not headers:
                        headers = [f"Columna {i + 1}" for i in range(len(rows_data[0]))]
                    debts.append({"headers": headers, "rows": rows_data})

            return {
                "success": True,
                "vehicle_data": vehicle_data,
                "notices": notices,
                "debts": debts,
            }

        except Exception as e:
            return {"success": False, "error": f"Error de automatización: {str(e)}"}
        finally:
            await browser.close()
