import subprocess
import sys
from pathlib import Path

import numpy as np
from faster_whisper import WhisperModel

from cortador import FFMPEG, PASTA_A_CORTAR, formatar_tempo, obter_escolha

EXTENSOES_MIDIA = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}
MODELO = "small"  # "base" é mais rápido e menor, mas erra mais em português
IDIOMA = "pt"


def listar_midias() -> list[Path]:
    PASTA_A_CORTAR.mkdir(exist_ok=True)
    return sorted(p for p in PASTA_A_CORTAR.iterdir() if p.is_file() and p.suffix.lower() in EXTENSOES_MIDIA)


def carregar_audio(arquivo: Path) -> np.ndarray:
    # O ffmpeg entrega o áudio já em 16 kHz mono. Não deixamos o faster-whisper abrir o arquivo
    # sozinho porque o leitor dele quebra no Python 3.14 (erro "metadata_errors").
    comando = [FFMPEG, "-nostdin", "-loglevel", "error", "-i", str(arquivo), "-ac", "1", "-ar", "16000", "-f", "s16le", "-"]
    bruto = subprocess.run(comando, capture_output=True).stdout
    return np.frombuffer(bruto, dtype=np.int16).astype(np.float32) / 32768.0


def transcrever(arquivo: Path, palavras: bool = False):
    # Devolve as frases aos poucos (gerador), para dar para mostrar o andamento em arquivos longos.
    # Com palavras=True cada frase traz também o horário de cada palavra.
    audio = carregar_audio(arquivo)
    if audio.size == 0:
        raise ValueError(f"Não encontrei áudio em {arquivo.name}.")
    modelo = WhisperModel(MODELO, device="cpu", compute_type="int8")
    frases, _ = modelo.transcribe(audio, language=IDIOMA, word_timestamps=palavras)
    for frase in frases:
        item = {"ini": frase.start, "fim": frase.end, "texto": frase.text.strip()}
        if palavras:
            item["palavras"] = [(p.word, round(p.start, 2), round(p.end, 2)) for p in frase.words]
        yield item


def salvar_transcricao(arquivo: Path, frases: list[dict]) -> Path:
    saida = arquivo.with_name(f"{arquivo.stem}_transcricao.txt")
    linhas = [f"[{formatar_tempo(f['ini'])}] {f['texto']}" for f in frases]
    # utf-8-sig para o Bloco de Notas do Windows abrir os acentos certos.
    saida.write_text("\n".join(linhas) + "\n", encoding="utf-8-sig")
    return saida


def main() -> None:
    midias = listar_midias()
    if not midias:
        print("Nenhum vídeo ou áudio encontrado na pasta 'a_cortar/'.")
        print("Coloque o arquivo nela e rode o programa novamente.")
        return

    print("=== Transcrição ===")
    print("Arquivos encontrados em a_cortar/:")
    for i, midia in enumerate(midias, start=1):
        print(f"  {i}. {midia.name}")
    print()
    print("  Q. Sair sem transcrever nada")

    escolha = obter_escolha(midias)
    if escolha.upper() == "Q":
        print("Nada foi transcrito. Até logo!")
        return

    arquivo = midias[int(escolha) - 1]
    print(f"Transcrevendo {arquivo.name}... (na primeira vez baixa o modelo, cerca de 460 MB)")
    frases = []
    for frase in transcrever(arquivo):
        print(f"[{formatar_tempo(frase['ini'])}] {frase['texto']}")
        frases.append(frase)

    saida = salvar_transcricao(arquivo, frases)
    print(f"Concluído: {saida.name} gerado com sucesso.")


if __name__ == "__main__":
    try:
        main()
    except ValueError as erro:
        print(erro)
        sys.exit(1)
