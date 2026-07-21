"""Consulta de deuda de patente y multas desde la terminal.

Uso:
    python cli.py ABC123                     # Santa Fe (por defecto)
    python cli.py ABC123 --jurisdiccion cordoba
    python cli.py                            # pregunta la patente por teclado
"""

import asyncio
import sys

from scraper import JURISDICCIONES, consultar_todo


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


def mostrar_patente(result: dict, jurisdiccion_nombre: str = ""):
    print("\n" + "=" * 50)
    sufijo = f" ({jurisdiccion_nombre})" if jurisdiccion_nombre else ""
    print(f"  DEUDA DE PATENTE{sufijo}")
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

    jurisdiccion = "santa_fe"
    if "--jurisdiccion" in args:
        i = args.index("--jurisdiccion")
        if i + 1 < len(args):
            jurisdiccion = args[i + 1]
            del args[i:i + 2]

    if jurisdiccion not in JURISDICCIONES:
        print(f"[-] Jurisdicción desconocida: {jurisdiccion}")
        print(f"    Opciones: {', '.join(JURISDICCIONES)}")
        return

    patente = args[0] if args else input("Ingrese la patente del vehículo: ")

    nombre = JURISDICCIONES[jurisdiccion]["nombre"]
    print(f"[+] Consultando patente {patente} en {nombre}...")
    result = asyncio.run(consultar_todo(patente, jurisdiccion))

    mostrar_patente(result.get("patente", {}), nombre)
    multas = result.get("multas", {})
    if not multas.get("no_aplica"):
        mostrar_multas(multas)


if __name__ == "__main__":
    main()
