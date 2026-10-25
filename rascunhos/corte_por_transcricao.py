"""RASCUNHO, não é uma ferramenta pronta. Guardado como base para a futura ferramenta visual.

Foi o que gerou o vídeo "..._corte_transcricao.mp4" a partir do original: tira do vídeo as lacunas
sem fala (achadas pela transcrição e confirmadas pelo volume do áudio) e mais uns cortes manuais.

Os cortes manuais e o "é"/"beleza" abaixo estão fixos para UM vídeo específico (gravação de
2026-10-25). Para outro vídeo, só a parte de "lacunas sem fala" (passo 3) serve como está.

Uso: python rascunhos/corte_por_transcricao.py   (precisa do vídeo na pasta a_cortar/)
"""
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import cortador as c
from transcrever import salvar_transcricao, transcrever

orig = c.PASTA_A_CORTAR / "Screenrecorder-2026-10-25-15-26-45-627.mp4"
dur = c.duracao_do_video(orig)

print("Transcrevendo o original (uns 70 s)...")
tr = list(transcrever(orig, palavras=True))
salvar_transcricao(orig, tr)
P = [(w.strip(), a, b) for s in tr for w, a, b in s["palavras"]]


def mmss1(x): return "%d:%04.1f" % (int(x) // 60, x % 60)


# --- energia (50 ms) para achar onde a voz de fato começa/termina
# Os horários de palavra do Whisper são aproximados (ele "estica" palavras sobre pausas).
raw = subprocess.run([c.FFMPEG, "-nostdin", "-loglevel", "error", "-i", str(orig), "-ac", "1", "-ar", "8000", "-f", "s16le", "-"], capture_output=True).stdout
a = np.frombuffer(raw, dtype=np.int16).astype(np.float64)
n = len(a) // 400
db = 20 * np.log10(np.sqrt((a[: n * 400].reshape(n, 400) ** 2).mean(axis=1)) / 32768 + 1e-9)
voz = db > -36  # o chiado dessa gravação fica em -44 dB; a fala, acima de -30 dB


def ultima_voz(t0, t1):
    i = [k for k in range(max(0, int(t0 * 20)), min(n, int(t1 * 20) + 1)) if voz[k]]
    return (i[-1] + 1) / 20 if i else t0


def primeira_voz(t0, t1):
    i = [k for k in range(max(0, int(t0 * 20)), min(n, int(t1 * 20) + 1)) if voz[k]]
    return i[0] / 20 if i else t1


def bloco(t0):
    # primeiro trecho contínuo de voz a partir de t0 (junta falhas menores que 0,2 s)
    k = next(k for k in range(int(t0 * 20), n) if voz[k]); ini = k; fim = k
    while fim + 1 < n and any(voz[fim + 1: fim + 5]):
        fim += 1
    while not voz[fim]: fim -= 1
    return ini / 20, (fim + 1) / 20


PAD = 0.25  # segundos de pausa que sobram em cada ponta de um corte
remover = []  # (ini, fim, motivo)

# --- 3) lacunas sem fala: pausas de 1 s ou mais entre palavras da transcrição
for i in range(len(P) - 1):
    pe, ns = P[i][2], P[i + 1][1]
    if ns - pe < 1.0: continue
    ini = ultima_voz(pe - 0.6, ns) + PAD
    fim = primeira_voz(ini, ns + 0.6) - PAD
    if fim - ini >= 0.4: remover.append((ini, fim, "sem fala"))
auto = len(remover)

# --- 4) cortes manuais: tempos lidos no vídeo "sem-pausas-1s", convertidos para o original
manter1s = c.trechos_a_manter(c.detectar_silencios(orig, dur, 1.0))


def para_orig(t):
    acum = 0.0
    for ini, fim in manter1s:
        comp = (fim if fim is not None else 1e9) - ini
        if t <= acum + comp: return ini + (t - acum)
        acum += comp


manuais = {1: (62.95, 71.67), 2: (105.01, 123.65), 3: (144.01, 156.97), 5: (182.37, 191.75), 6: (258.93, 267.29)}
for k, (x, y) in manuais.items():
    remover.append((para_orig(x), para_orig(y), f"manual {k}"))

# corte 4 refeito: tira o "beleza" e o silêncio, mantém "agora vou testar a nova ferramenta"
bel = next(w for w in P if w[0].lower().strip(",.") == "beleza" and 198 < w[1] < 201)
ag = next(w for w in P if w[0].lower() == "agora" and w[1] > bel[2])
ini4 = ultima_voz(bel[1] - 1.0, bel[1] - 0.3) + PAD
bel_fim = bloco(bel[1] - 0.1)[1]
fim4 = bloco(bel_fim + 0.1)[0] - PAD  # logo antes de "agora"
remover.append((ini4, fim4, "manual 4 (beleza + silêncio)"))

# "é" do começo: pausa + vogal longa
e = next(w for w in P if w[0] in ("é", "É") and 20 < w[1] < 22)
ini_e = ultima_voz(e[1] - 0.6, e[1] + 0.2) + 0.15
fim_e = bloco(ini_e)[1]
remover.append((ini_e, fim_e + 0.1, "'é' do começo"))

# --- 5) junta o que se sobrepõe
remover.sort()
fund = []
for ini, fim, mot in remover:
    if fund and ini <= fund[-1][1] + 0.05:
        fund[-1] = (fund[-1][0], max(fund[-1][1], fim), fund[-1][2] + " + " + mot)
    else:
        fund.append((ini, fim, mot))

total = sum(f - i for i, f, _ in fund)
linhas = [f"{len(fund)} trechos removidos, {total:.0f}s no total ({auto} lacunas sem fala + cortes manuais)\n"]
for i, f, mot in fund:
    dentro = " ".join(w for w, x, y in P if x >= i - 0.05 and y <= f + 0.05)
    linhas.append(f"{mmss1(i)} -> {mmss1(f)} ({f - i:4.1f}s)  [{mot}]  fala removida: {dentro or '-'}")
texto = "\n".join(linhas)
orig.with_name(orig.stem + "_corte_transcricao_lista.txt").write_text(texto + "\n", encoding="utf-8-sig")
print(texto)

# --- 6) gera o vídeo a partir do original (mesma montagem do cortador.py)
manter, cur = [], 0.0
for i, f, _ in fund:
    manter.append((cur, i)); cur = f
manter.append((cur, None))
partes = []
for k, (i, f) in enumerate(manter):
    lim = f"start={i:.3f}" + (f":end={f:.3f}" if f is not None else "")
    partes += [f"[0:v]trim={lim},setpts=PTS-STARTPTS[v{k}]", f"[0:a]atrim={lim},asetpts=PTS-STARTPTS[a{k}]"]
partes.append("".join(f"[v{k}][a{k}]" for k in range(len(manter))) + f"concat=n={len(manter)}:v=1:a=1[v][a]")
saida = orig.with_name(orig.stem + "_corte_transcricao.mp4")
r = subprocess.run([c.FFMPEG, "-nostdin", "-y", "-loglevel", "error", "-i", str(orig), "-filter_complex", ";".join(partes),
                    "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(saida)],
                   capture_output=True, text=True)
print(r.stderr or "ok")
print(saida.name, f"{saida.stat().st_size / 1048576:.1f} MB", "duração", c.formatar_tempo(c.duracao_do_video(saida)), "(original", c.formatar_tempo(dur) + ")")
