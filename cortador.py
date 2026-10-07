import os
import re
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg

if sys.platform == "win32":
    os.system("chcp 65001 > nul")
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdin.reconfigure(encoding="utf-8")

PASTA_A_CORTAR = Path(__file__).resolve().parent / "a_cortar"
EXTENSOES = {".mp4", ".mov", ".mkv", ".avi", ".webm"}
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()


def listar_videos() -> list[Path]:
    PASTA_A_CORTAR.mkdir(exist_ok=True)
    videos = [
        p for p in PASTA_A_CORTAR.iterdir()
        if p.is_file() and p.suffix.lower() in EXTENSOES and "_corte_" not in p.stem
    ]
    return sorted(videos)


def exibir_menu(videos: list[Path]) -> None:
    if not videos:
        print("Nenhum vídeo encontrado na pasta 'a_cortar/'.")
        print("Coloque um vídeo nela e rode o programa novamente.")
        sys.exit(0)

    print("=== Cortador de Vídeo ===")
    print("Vídeos encontrados em a_cortar/:")
    for i, video in enumerate(videos, start=1):
        print(f"  {i}. {video.name}")
    print()
    print("  Q. Sair sem cortar nada")


def obter_escolha(videos: list[Path]) -> str:
    while True:
        escolha = input("Escolha uma opção: ").strip()

        if escolha.upper() == "Q":
            return "Q"
        if escolha.isdigit() and 1 <= int(escolha) <= len(videos):
            return escolha

        print("Opção inválida. Digite o número de um vídeo da lista ou Q para sair.")


def perguntar_sim_nao(pergunta: str) -> bool:
    respostas_sim = {"s", "sim"}
    respostas_nao = {"n", "nao", "não"}
    while True:
        resposta = input(pergunta).strip().lower()
        if resposta in respostas_sim:
            return True
        if resposta in respostas_nao:
            return False


def para_segundos(texto: str) -> int | None:
    # Aceita mm:ss (36:58) ou h:mm:ss (1:02:03). Devolve None se o formato for inválido.
    partes = texto.strip().split(":")
    if len(partes) not in (2, 3) or not all(p.isdigit() for p in partes):
        return None
    numeros = [int(p) for p in partes]
    if numeros[-1] >= 60 or (len(numeros) == 3 and numeros[1] >= 60):
        return None
    total = 0
    for n in numeros:
        total = total * 60 + n
    return total


def formatar_tempo(segundos: float) -> str:
    segundos = int(segundos)
    h, resto = divmod(segundos, 3600)
    m, s = divmod(resto, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def duracao_do_video(video: Path) -> float | None:
    # O ffmpeg sem saída devolve erro, mas imprime a duração no stderr.
    r = subprocess.run([FFMPEG, "-nostdin", "-i", str(video)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    achou = re.search(r"Duration: (\d+):(\d+):(\d+)", r.stderr)
    if not achou:
        return None
    h, m, s = (int(x) for x in achou.groups())
    return h * 3600 + m * 60 + s


def pedir_tempo(pergunta: str) -> int:
    while True:
        segundos = para_segundos(input(pergunta))
        if segundos is not None:
            return segundos
        print("Formato inválido. Use mm:ss (ex.: 36:58) ou h:mm:ss (ex.: 1:02:03).")


def pedir_intervalo(duracao: float | None) -> tuple[int, int]:
    while True:
        inicio = pedir_tempo("Início do corte (mm:ss): ")
        fim = pedir_tempo("Fim do corte (mm:ss): ")

        if fim <= inicio:
            print("O fim precisa ser depois do início. Tente de novo.")
            continue
        if duracao is not None and inicio >= duracao:
            print(f"O início passa do fim do vídeo, que tem {formatar_tempo(duracao)}. Tente de novo.")
            continue
        if duracao is not None and fim > duracao:
            print(f"Aviso: o vídeo só tem {formatar_tempo(duracao)}; o corte vai até o final dele.")
        return inicio, fim


def cortar(video: Path, inicio: int, fim: int) -> Path | None:
    saida = video.with_name(f"{video.stem}_corte_{inicio}-{fim}.mp4")
    print(f"Cortando {formatar_tempo(inicio)} até {formatar_tempo(fim)}... (pode levar alguns instantes)")

    # Reencoda (libx264/aac) para o corte sair exato; copiar o fluxo erraria o início por vários segundos.
    comando = [
        FFMPEG, "-nostdin", "-y", "-loglevel", "error",
        "-ss", str(inicio), "-to", str(fim), "-i", str(video),
        "-c:v", "libx264", "-c:a", "aac", str(saida),
    ]
    resultado = subprocess.run(comando, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if resultado.returncode != 0:
        print(f"Erro ao cortar {video.name}:")
        print(resultado.stderr.strip())
        return None

    tamanho_mb = saida.stat().st_size / (1024 * 1024)
    print(f"Concluído: {saida.name} gerado com sucesso ({tamanho_mb:.1f} MB).")
    return saida


def main() -> None:
    videos = listar_videos()
    exibir_menu(videos)

    escolha = obter_escolha(videos)
    if escolha.upper() == "Q":
        print("Nenhum vídeo foi cortado. Até logo!")
        return

    video = videos[int(escolha) - 1]
    duracao = duracao_do_video(video)
    if duracao is not None:
        print(f"Duração do vídeo: {formatar_tempo(duracao)}")

    while True:
        inicio, fim = pedir_intervalo(duracao)
        cortar(video, inicio, fim)
        if not perguntar_sim_nao("Cortar outro trecho do mesmo vídeo? (s/n): "):
            break

    print("Até logo!")


if __name__ == "__main__":
    main()
