"""
Intelligence Hub v2.0 — Entry point para executável PyInstaller.

Quando compilado com PyInstaller (--onefile), este arquivo é o ponto de entrada.
Garante que:
  1. multiprocessing.freeze_support() é chamado antes de qualquer coisa
  2. O CWD é setado para o diretório do .exe (para config/, output/, data/)
  3. Os módulos bundled são acessíveis via sys.path
  4. Configuração e pastas são criadas na primeira execução
"""
from __future__ import annotations

import multiprocessing
import os
import sys
from pathlib import Path


# ────────────────────────────────────────────────────────────────────────────
# OBRIGATÓRIO: deve ser a primeiríssima coisa no bloco __main__
# ────────────────────────────────────────────────────────────────────────────

def _get_exe_dir() -> Path:
    """Diretório onde o .exe (ou o script dev) reside."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent.resolve()
    # Modo desenvolvimento: raiz do projeto (um nível acima de src/)
    return Path(__file__).parent.parent.resolve()


def _setup_env() -> tuple[Path, Path]:
    """
    Configura o ambiente de execução.
    Retorna (exe_dir, bundle_dir).
    """
    exe_dir = _get_exe_dir()

    # Muda o CWD para o diretório do exe → todos os caminhos relativos
    # (config/config.yaml, output/, data/, .env) funcionam corretamente.
    os.chdir(exe_dir)

    if getattr(sys, "frozen", False):
        bundle_dir = Path(sys._MEIPASS).resolve()
        # Adiciona o bundle ao sys.path para que 'import webapp' funcione
        for p in (str(bundle_dir), str(bundle_dir / "src")):
            if p not in sys.path:
                sys.path.insert(0, p)
    else:
        bundle_dir = exe_dir
        src_path = str(Path(__file__).parent)
        if src_path not in sys.path:
            sys.path.insert(0, src_path)

    return exe_dir, bundle_dir


def _ensure_first_run(exe_dir: Path, bundle_dir: Path) -> None:
    """Cria pastas e copia configuração padrão na primeira execução."""
    import shutil

    # Pastas de trabalho
    for folder in ("config", "output", "data", "logs"):
        (exe_dir / folder).mkdir(exist_ok=True)

    # config.yaml
    config_dst = exe_dir / "config" / "config.yaml"
    if not config_dst.exists():
        for candidate in (
            bundle_dir / "hub_config" / "config.example.yaml",  # dentro do bundle
            exe_dir / "config" / "config.example.yaml",         # modo dev
        ):
            if candidate.exists():
                shutil.copy(candidate, config_dst)
                print("[setup] Configuração padrão criada em config/config.yaml")
                print("        Edite o arquivo para personalizar regiões e palavras-chave.")
                break

    # .env
    env_dst = exe_dir / ".env"
    if not env_dst.exists():
        for candidate in (
            bundle_dir / ".env.example",
            exe_dir / ".env.example",
        ):
            if candidate.exists():
                shutil.copy(candidate, env_dst)
                break


def _print_banner(host: str, port: int) -> None:
    print()
    print("  +--------------------------------------------------+")
    print("  |  Intelligence Hub v2.0                           |")
    print(f"  |  Acesse  ->  http://{host}:{port}                 |")
    print("  |  Pressione Ctrl+C para encerrar                  |")
    print("  +--------------------------------------------------+")
    print()


# ────────────────────────────────────────────────────────────────────────────
# Entry point
# ────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # DEVE ser a primeira instrução — necessário para multiprocessing em modo frozen
    multiprocessing.freeze_support()

    exe_dir, bundle_dir = _setup_env()
    _ensure_first_run(exe_dir, bundle_dir)

    import argparse
    parser = argparse.ArgumentParser(description="Intelligence Hub v2.0")
    parser.add_argument("--host", default="127.0.0.1", help="Host (padrão: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8787, help="Porta (padrão: 8787)")
    parser.add_argument("--no-browser", action="store_true", help="Não abrir navegador")
    args = parser.parse_args()

    _print_banner(args.host, args.port)

    # Abre o navegador automaticamente após 3 segundos
    if not args.no_browser:
        import threading, webbrowser, time

        def _open():
            time.sleep(3)
            webbrowser.open(f"http://{args.host}:{args.port}")

        threading.Thread(target=_open, daemon=True).start()

    # Inicia o servidor FastAPI/uvicorn
    from webapp import start_server
    start_server(host=args.host, port=args.port)
