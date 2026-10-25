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
LIMITE_SILENCIO_DB = -30
PAUSA_MINIMA_PADRAO = 2.0
FOLGA_EMENDA = 0.3  # segundos de pausa que sobram em cada ponta ao remover um silêncio


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


def detectar_silencios(video: Path, duracao: float, minimo: float) -> list[tuple[float, float]]:
    # O ruído de fundo de gravação de tela costuma ficar perto de -44 dB e a fala perto de -26 dB;
    # -30 dB separa os dois. Um limite mais baixo (ex.: -38 dB) não acha pausa nenhuma.
    comando = [
        FFMPEG, "-nostdin", "-i", str(video),
        "-af", f"silencedetect=noise={LIMITE_SILENCIO_DB}dB:d={minimo}",
        "-f", "null", "-",
    ]
    r = subprocess.run(comando, capture_output=True, text=True, encoding="utf-8", errors="replace")

    silencios = []
    inicio = None
    for achou in re.finditer(r"silence_start: (-?[\d.]+)|silence_end: ([\d.]+)", r.stderr):
        if achou.group(1) is not None:
            inicio = max(0.0, float(achou.group(1)))
        elif inicio is not None:
            silencios.append((inicio, float(achou.group(2))))
            inicio = None
    if inicio is not None:  # silêncio que vai até o final do vídeo
        silencios.append((inicio, float(duracao)))
    return silencios


def trechos_a_manter(silencios: list[tuple[float, float]]) -> list[tuple[float, float | None]]:
    # Tira cada pausa menos a folga nas duas pontas, senão a emenda fica "atropelada".
    # O último trecho vai sem fim (None) para não perder a ponta do vídeo.
    manter = []
    cursor = 0.0
    for inicio, fim in silencios:
        if fim - inicio <= 2 * FOLGA_EMENDA:
            continue
        manter.append((cursor, inicio + FOLGA_EMENDA))
        cursor = fim - FOLGA_EMENDA
    manter.append((cursor, None))
    return manter


def remover_pausas(video: Path, duracao: float, minimo: float) -> Path | None:
    print(f"Procurando pausas de {minimo:g}s ou mais...")
    silencios = detectar_silencios(video, duracao, minimo)
    manter = trechos_a_manter(silencios)
    if len(manter) == 1:
        print("Nenhuma pausa desse tamanho encontrada. Nada a cortar.")
        return None

    removido = sum(fim - inicio - 2 * FOLGA_EMENDA for inicio, fim in silencios if fim - inicio > 2 * FOLGA_EMENDA)
    print(f"{len(manter) - 1} pausas encontradas, cerca de {formatar_tempo(removido)} a menos no vídeo:")
    for inicio, fim in silencios:
        print(f"  {formatar_tempo(inicio)} -> {formatar_tempo(fim)} ({fim - inicio:.1f}s)")

    partes = []
    for i, (inicio, fim) in enumerate(manter):
        limites = f"start={inicio:.3f}" + (f":end={fim:.3f}" if fim is not None else "")
        partes.append(f"[0:v]trim={limites},setpts=PTS-STARTPTS[v{i}]")
        partes.append(f"[0:a]atrim={limites},asetpts=PTS-STARTPTS[a{i}]")
    entradas = "".join(f"[v{i}][a{i}]" for i in range(len(manter)))
    partes.append(f"{entradas}concat=n={len(manter)}:v=1:a=1[v][a]")

    saida = video.with_name(f"{video.stem}_corte_sem-pausas-{minimo:g}s.mp4")
    print("Gerando o vídeo sem as pausas... (pode levar alguns minutos)")
    comando = [
        FFMPEG, "-nostdin", "-y", "-loglevel", "error",
        "-i", str(video), "-filter_complex", ";".join(partes),
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(saida),
    ]
    resultado = subprocess.run(comando, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if resultado.returncode != 0:
        print(f"Erro ao processar {video.name}:")
        print(resultado.stderr.strip())
        return None

    nova = duracao_do_video(saida)
    tamanho_mb = saida.stat().st_size / (1024 * 1024)
    duracao_nova = f", agora com {formatar_tempo(nova)}" if nova is not None else ""
    print(f"Concluído: {saida.name} gerado com sucesso ({tamanho_mb:.1f} MB{duracao_nova}).")
    return saida


def pedir_pausa_minima() -> float:
    while True:
        texto = input(f"Pausa mínima a remover, em segundos (Enter = {PAUSA_MINIMA_PADRAO:g}): ").strip().replace(",", ".")
        if not texto:
            return PAUSA_MINIMA_PADRAO
        try:
            valor = float(texto)
        except ValueError:
            valor = 0
        if valor >= 0.5:
            return valor
        print("Digite um número de segundos, a partir de 0,5 (ex.: 2 ou 1).")


def obter_modo() -> str:
    print()
    print("O que fazer com esse vídeo?")
    print("  1. Cortar um trecho (início e fim)")
    print("  2. Remover as pausas (silêncios)")
    while True:
        modo = input("Escolha uma opção: ").strip()
        if modo in ("1", "2"):
            return modo
        print("Opção inválida. Digite 1 ou 2.")


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

    if obter_modo() == "2":
        if duracao is None:
            print("Não consegui ler a duração do vídeo; não dá para remover pausas.")
            return
        while True:
            remover_pausas(video, duracao, pedir_pausa_minima())
            if not perguntar_sim_nao("Gerar outra versão com outra pausa mínima? (s/n): "):
                break
        print("Até logo!")
        return

    while True:
        inicio, fim = pedir_intervalo(duracao)
        cortar(video, inicio, fim)
        if not perguntar_sim_nao("Cortar outro trecho do mesmo vídeo? (s/n): "):
            break

    print("Até logo!")


if __name__ == "__main__":
    main()
