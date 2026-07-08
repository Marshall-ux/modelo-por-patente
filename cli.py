"""Consulta de deuda de patentes desde la línea de comandos.

Uso:
    python cli.py ABC123
    python cli.py ABC123 --visible   # muestra el navegador (no headless)
    python cli.py                    # pregunta la patente por teclado
"""

import asyncio
import sys

from scraper import consultar_patente_data


def print_table(headers, rows):
    if not rows:
        print("  (Sin datos)")
        return
    widths = [len(str(h)) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            if i < len(widths):
                widths[i] = max(widths[i], len(str(val)))
            else:
                widths.append(len(str(val)))

    header_str = " | ".join(f"{str(h).ljust(widths[i])}" for i, h in enumerate(headers))
    print("  " + header_str)
    print("  " + "-+-".join("-" * w for w in widths))
    for row in rows:
        print("  " + " | ".join(f"{str(v).ljust(widths[i])}" for i, v in enumerate(row)))


def mostrar_resultado(result: dict):
    if not result.get("success"):
        print(f"[-] {result.get('error', 'Error desconocido.')}")
        return

    vehicle_data = result.get("vehicle_data", [])
    if vehicle_data:
        print("\n=== DATOS DEL VEHÍCULO ===")
        for item in vehicle_data:
            print(f"  * {item}")

    notices = result.get("notices", [])
    if notices:
        print("\n=== NOTAS / AVISOS DE LA JURISDICCIÓN ===")
        for nt in notices:
            print(f"  * {nt}")

    debts = result.get("debts", [])
    if debts:
        for idx, table in enumerate(debts, start=1):
            print(f"\n--- Detalle/Resumen de Deuda (Tabla {idx}) ---")
            print_table(table["headers"], table["rows"])
    else:
        print("\n  No se encontraron deudas activas.")


def main():
    args = [a for a in sys.argv[1:]]
    headless = "--visible" not in args
    args = [a for a in args if a != "--visible"]

    patente = args[0] if args else input("Ingrese la patente del vehículo: ")

    print(f"[+] Consultando patente: {patente}")
    result = asyncio.run(consultar_patente_data(patente, headless=headless))
    mostrar_resultado(result)


if __name__ == "__main__":
    main()
