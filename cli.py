"""Consulta de deuda de patente (Santa Fe) y multas (Rosario) desde la terminal.

Uso:
    python cli.py ABC123
    python cli.py                    # pregunta la patente por teclado
"""

import asyncio
import sys

from scraper import consultar_todo


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


def mostrar_patente(result: dict):
    print("\n" + "=" * 50)
    print("  DEUDA DE PATENTE (Santa Fe)")
    print("=" * 50)
    if not result.get("success"):
        print(f"[-] {result.get('error', 'Error desconocido.')}")
        return

    for item in result.get("vehicle_data", []):
        print(f"  * {item}")

    notices = result.get("notices", [])
    if notices:
        print("\n  Notas / avisos:")
        for nt in notices:
            print(f"  * {nt}")

    debts = result.get("debts", [])
    if debts:
        for idx, table in enumerate(debts, start=1):
            print(f"\n  --- Detalle de Deuda (Tabla {idx}) ---")
            print_table(table["headers"], table["rows"])
    else:
        print("\n  No se encontraron deudas activas.")


def mostrar_multas(result: dict):
    print("\n" + "=" * 50)
    print("  MULTAS DE TRÁNSITO (Rosario)")
    print("=" * 50)
    if not result.get("success"):
        print(f"[-] {result.get('error', 'Error desconocido.')}")
        return

    if result.get("libre_multas") or not result.get("fines"):
        print("  El vehículo no registra multas pendientes.")
        return

    for idx, fine in enumerate(result.get("fines", []), start=1):
        print(f"\n  [{idx}] Acta: {fine.get('acta', '-')}  ({fine.get('estado', '-')})")
        for k, v in fine.get("detalles", {}).items():
            print(f"      - {k}: {v}")
        if fine.get("ver_acta"):
            print(f"      Ver acta: {fine['ver_acta']}")


def main():
    args = sys.argv[1:]
    patente = args[0] if args else input("Ingrese la patente del vehículo: ")

    print(f"[+] Consultando patente: {patente} (patente + multas en paralelo)...")
    result = asyncio.run(consultar_todo(patente))

    mostrar_patente(result.get("patente", {}))
    mostrar_multas(result.get("multas", {}))


if __name__ == "__main__":
    main()
