"""Lógica de scraping compartida.

Consulta dos fuentes por patente de vehículo:
  - Deuda de patente en el portal de la Provincia de Santa Fe
    (https://www.santafe.gov.ar/e-pt-liq-deuda/), resolviendo el captcha Altcha.
  - Multas de tránsito en el portal de la Municipalidad de Rosario
    (https://www.rosario.gob.ar/gdm/), incluyendo la descarga del PDF del recibo.

Todas las funciones de consulta devuelven un dict con la clave "success".
La app web (app.py) y la CLI (cli.py) reutilizan este módulo.
"""

import asyncio
import os
import re
import tempfile
import urllib.parse

from playwright.async_api import async_playwright

# --- Portales ---
SANTA_FE_URL = "https://www.santafe.gov.ar/e-pt-liq-deuda/"
ROSARIO_URL = "https://www.rosario.gob.ar/gdm/patente.do?accion=ir"
ROSARIO_BASE = "https://www.rosario.gob.ar"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def normalizar_patente(patente: str) -> str:
    """Limpia la patente: mayúsculas, sin espacios ni guiones."""
    return patente.strip().upper().replace(" ", "").replace("-", "")


async def _nueva_pagina(p, stealth: bool = False):
    """Crea browser + context + page. Con stealth=True aplica los ajustes
    anti-detección que necesita el portal de Rosario (reCAPTCHA v3)."""
    launch_args = ["--disable-blink-features=AutomationControlled"] if stealth else []
    browser = await p.chromium.launch(headless=True, args=launch_args)

    # ignore_https_errors: necesario cuando se corre detrás de un proxy
    # corporativo con inspección SSL, donde Chromium no confía en el
    # certificado raíz interceptor (net::ERR_CERT_AUTHORITY_INVALID).
    context_kwargs = {"user_agent": USER_AGENT, "ignore_https_errors": True}
    if stealth:
        context_kwargs.update(
            locale="es-AR",
            timezone_id="America/Argentina/Buenos_Aires",
            viewport={"width": 1280, "height": 720},
        )
    context = await browser.new_context(**context_kwargs)
    page = await context.new_page()
    if stealth:
        await page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
    return browser, page


# ---------------------------------------------------------------------------
# Santa Fe: deuda de patente
# ---------------------------------------------------------------------------
async def consultar_patente_data(patente: str) -> dict:
    patente = normalizar_patente(patente)
    if not patente:
        return {"success": False, "error": "La patente ingresada está vacía."}

    async with async_playwright() as p:
        browser, page = await _nueva_pagina(p)
        try:
            await page.goto(SANTA_FE_URL, timeout=30000)

            await page.wait_for_selector("#nupatente", timeout=15000)
            await page.fill("#nupatente", patente)

            # Captcha Altcha (proof-of-work)
            checkbox_selector = 'altcha-widget input[type="checkbox"]'
            await page.wait_for_selector(checkbox_selector, timeout=10000)
            await page.click(checkbox_selector)
            await page.wait_for_selector(
                'altcha-widget .altcha[data-state="verified"]', timeout=15000
            )

            await page.click('input[name="Aceptar"]')
            await page.wait_for_load_state("domcontentloaded")

            # Si seguimos en la página de entrada, hubo un error de validación
            is_input_page = await page.locator("#nupatente").count() > 0
            if is_input_page:
                error_selector = ".ui-state-error"
                if await page.locator(error_selector).count() > 0:
                    error_texts = []
                    for loc in await page.locator(error_selector).all():
                        txt = await loc.inner_text()
                        error_texts.append(txt.replace("\n", " ").strip())
                    error_clean = re.sub(r"\s+", " ", " | ".join(error_texts))
                    return {"success": False, "error": error_clean}

                body_text = await page.inner_text("body")
                if "DOMINIO INEXISTENTE" in body_text:
                    return {"success": False, "error": "Dominio inexistente."}
                return {
                    "success": False,
                    "error": "Error de validación desconocido en el portal de patentes.",
                }

            # Datos del vehículo
            vehicle_data = []
            for label in await page.locator(".form-label label").all():
                text = re.sub(r"\s+", " ", await label.inner_text()).strip()
                if text:
                    text = text.replace(" :", ":").replace(" - ", " | ")
                    vehicle_data.append(text)

            # Avisos / notas
            notices = []
            for el in await page.locator(".ui-state-error").all():
                txt = re.sub(r"\s+", " ", await el.inner_text()).strip()
                if txt and txt not in notices:
                    notices.append(txt)

            # Tablas de deuda
            debts = []
            for table in await page.locator("table").all():
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
            return {
                "success": False,
                "error": f"Error de automatización en portal de patentes: {str(e)}",
            }
        finally:
            await browser.close()


# ---------------------------------------------------------------------------
# Rosario: multas de tránsito
# ---------------------------------------------------------------------------
async def consultar_multas_data(patente: str) -> dict:
    patente = normalizar_patente(patente)
    if not patente:
        return {"success": False, "error": "La patente ingresada está vacía."}

    async with async_playwright() as p:
        browser, page = await _nueva_pagina(p, stealth=True)
        try:
            await page.goto(ROSARIO_URL, timeout=30000)

            await page.wait_for_selector("#patente", timeout=15000)
            await page.fill("#patente", patente)

            # Esperar la carga del reCAPTCHA v3
            await page.wait_for_timeout(3000)

            await asyncio.gather(
                page.wait_for_load_state("domcontentloaded"),
                page.click('button:has-text("Consultar")'),
            )
            await page.wait_for_timeout(1000)

            # Resumen de error
            error_selector = ".govuk-error-summary"
            if await page.locator(error_selector).count() > 0:
                err_text = await page.locator(error_selector).inner_text()
                return {"success": False, "error": re.sub(r"\s+", " ", err_text).strip()}

            # Tarjetas de multas
            cards = await page.locator(".govuk-summary-card").all()
            fines_list = []

            if cards:
                for card in cards:
                    title = re.sub(
                        r"\s+", " ",
                        await card.locator(".govuk-summary-card__title").inner_text(),
                    ).strip()

                    category = "Infracción"
                    try:
                        category = await card.evaluate(
                            "el => el.closest('.govuk-tabs__panel')"
                            "?.querySelector('h2')?.innerText || 'Acta'"
                        )
                        category = re.sub(r"\s+", " ", category).strip()
                    except Exception:
                        pass

                    details = {}
                    for row in await card.locator(".govuk-summary-list__row").all():
                        key_loc = row.locator("xpath=./dt")
                        val_loc = row.locator("xpath=./dd")
                        if await key_loc.count() > 0 and await val_loc.count() > 0:
                            key_text = re.sub(
                                r"\s+", " ", await key_loc.first.inner_text()
                            ).strip()

                            details_text = val_loc.locator(".govuk-details__summary-text")
                            if await details_text.count() > 0:
                                val_text = await details_text.first.inner_text()
                            else:
                                val_text = await val_loc.inner_text()
                            val_text = re.sub(r"\s+", " ", val_text).strip()

                            if key_text:
                                details[key_text.replace(":", "").strip()] = val_text

                    # Link "ver acta"
                    ver_acta_url = None
                    try:
                        ver_acta_loc = card.locator('a:has-text("ver acta")')
                        if await ver_acta_loc.count() > 0:
                            onclick_text = await ver_acta_loc.first.get_attribute("onclick")
                            if onclick_text:
                                match_url = re.search(
                                    r"openNewWindow\(event,\s*'([^']+)'\)", onclick_text
                                )
                                if match_url:
                                    ver_acta_url = ROSARIO_BASE + match_url.group(1)
                    except Exception:
                        pass

                    # Botón/link para descargar recibo
                    ver_recibo_url = None
                    try:
                        btn_data = await card.evaluate(
                            """el => {
                                let next = el.nextElementSibling;
                                while (next) {
                                    if (next.classList.contains('govuk-summary-card') || next.tagName === 'H3') {
                                        break;
                                    }
                                    if (next.tagName === 'BUTTON' && (next.id.startsWith('verRecibo_') || next.id.startsWith('generarRecibo_'))) {
                                        return {
                                            id: next.id,
                                            comprobante: next.getAttribute('data-comprobante') || next.getAttribute('data-cuenta'),
                                            tipodeuda: next.getAttribute('data-tipodeuda')
                                        };
                                    }
                                    next = next.nextElementSibling;
                                }
                                return null;
                            }"""
                        )
                        if btn_data and btn_data.get("comprobante") and btn_data.get("tipodeuda"):
                            comp = urllib.parse.quote(btn_data["comprobante"])
                            td = urllib.parse.quote(btn_data["tipodeuda"])
                            ver_recibo_url = (
                                f"/api/recibo?patente={patente}"
                                f"&comprobante={comp}&tipodeuda={td}"
                            )
                    except Exception:
                        pass

                    fines_list.append({
                        "acta": title,
                        "estado": category,
                        "detalles": details,
                        "ver_acta": ver_acta_url,
                        "ver_recibo": ver_recibo_url,
                    })

                return {"success": True, "fines": fines_list, "libre_multas": False}

            # Sin tarjetas: ¿está limpio?
            if await page.locator("#emitirInforme").count() > 0:
                return {"success": True, "fines": [], "libre_multas": True}

            body_text = (await page.inner_text("body")).lower()
            if "no se encontraron" in body_text or "sin actas" in body_text:
                return {"success": True, "fines": [], "libre_multas": True}

            return {
                "success": False,
                "error": "No se encontraron actas de multas ni el botón de reporte.",
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Error de automatización en portal de multas: {str(e)}",
            }
        finally:
            await browser.close()


async def consultar_todo(patente: str) -> dict:
    """Consulta deuda de patente (Santa Fe) y multas (Rosario) en paralelo."""
    res_patente, res_multas = await asyncio.gather(
        consultar_patente_data(patente),
        consultar_multas_data(patente),
    )
    return {"patente": res_patente, "multas": res_multas}


# ---------------------------------------------------------------------------
# Rosario: descarga del PDF del recibo
# ---------------------------------------------------------------------------
async def download_receipt_pdf_data(patente: str, comprobante: str, tipodeuda: str) -> bytes:
    patente = normalizar_patente(patente)
    if not patente:
        raise Exception("La patente ingresada está vacía.")

    async with async_playwright() as p:
        browser, page = await _nueva_pagina(p, stealth=True)
        try:
            await page.goto(ROSARIO_URL, timeout=30000)

            await page.wait_for_selector("#patente", timeout=15000)
            await page.fill("#patente", patente)
            await page.wait_for_timeout(3000)

            await asyncio.gather(
                page.wait_for_load_state("domcontentloaded"),
                page.click('button:has-text("Consultar")'),
            )
            await page.wait_for_timeout(1000)

            comp = urllib.parse.quote(comprobante)
            td = urllib.parse.quote(tipodeuda)
            receipt_url = (
                f"{ROSARIO_BASE}/gdm/comprobante.do?accion=seleccionar"
                f"&id={comp}&tipoDeuda={td}"
            )
            await page.goto(receipt_url, timeout=15000)
            await page.wait_for_timeout(2000)

            button_selector = (
                "#generarPagoVoluntarioMinimo, #generarPagoVoluntarioSinDesc, "
                "#generarPagoVoluntarioConDesc, button:has-text('Reimprimir')"
            )
            await page.wait_for_selector(button_selector, timeout=15000)

            clicked = False
            for selector in [
                "#generarPagoVoluntarioMinimo",
                "#generarPagoVoluntarioSinDesc",
                "#generarPagoVoluntarioConDesc",
                "button:has-text('Reimprimir')",
            ]:
                if await page.locator(selector).count() > 0:
                    async with page.expect_navigation(timeout=15000):
                        await page.click(selector)
                    clicked = True
                    break

            if not clicked:
                async with page.expect_navigation(timeout=15000):
                    await page.evaluate(
                        """() => {
                            document.forms[0].accion.value = 'reimprimir';
                            document.forms[0].submit();
                        }"""
                    )

            await page.wait_for_timeout(2000)

            print_selector = (
                'a[id^="imprimir-pv-"], a[id^="imprimir-rec-"], a:has-text("Imprimir")'
            )
            await page.wait_for_selector(print_selector, timeout=15000)

            async with page.expect_download(timeout=15000) as download_info:
                await page.click(print_selector)
            download = await download_info.value

            temp_path = os.path.join(
                tempfile.gettempdir(),
                f"recibo_{patente}_{download.suggested_filename}",
            )
            await download.save_as(temp_path)
            with open(temp_path, "rb") as f:
                pdf_bytes = f.read()
            try:
                os.remove(temp_path)
            except OSError:
                pass

            return pdf_bytes

        except Exception as e:
            raise Exception(f"Error automatizando descarga de recibo: {str(e)}")
        finally:
            await browser.close()
