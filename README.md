# Cortador de Vídeo

Corta um trecho de um vídeo (por exemplo, uma entrevista gravada) e salva como um novo arquivo `.mp4`. Você escolhe o vídeo num menu e digita o início e o fim do corte.

## Antes de usar

Você precisa ter o Python instalado na máquina. Se `python --version` funcionar no terminal, já está tudo certo. **Não precisa instalar o ffmpeg**: ele vem junto com a dependência abaixo.

## Instalação (só precisa fazer uma vez)

1. Abra um terminal na pasta deste projeto.
2. Rode:
   ```
   pip install -r requirements.txt
   ```
3. Esse passo baixa cerca de 30 MB (o programa de vídeo que faz o corte). É normal levar um tempinho.

## Como usar

1. Coloque o vídeo dentro da pasta `a_cortar/`.
2. Abra um terminal nesta pasta e rode `python cortador.py` (ou dê duplo clique em `cortador.py`).
3. Escolha no menu o número do vídeo, ou `Q` para sair.
4. Digite o **início** e o **fim** do corte no formato `mm:ss` (ex.: `36:58` e `38:45`). Para vídeos com mais de 1 hora, use `h:mm:ss` (ex.: `1:02:03`).
5. Pronto. O corte aparece ao lado do vídeo original, dentro de `a_cortar/`, com o nome `<nome do vídeo>_corte_<início>-<fim>.mp4` (início e fim em segundos).
6. O programa pergunta se você quer cortar outro trecho do mesmo vídeo. Útil para ajustar o fim se o primeiro corte ficou curto ou comprido.

## Remover pausas (silêncios)

Depois de escolher o vídeo, a opção **2** apaga os trechos em que ninguém fala (útil em gravação de tela em que você espera algo carregar). O programa pergunta a **pausa mínima** em segundos (Enter = 2): só some silêncio com essa duração ou mais. Valores menores (ex.: 1) cortam mais e deixam o vídeo mais "seco". Sobram 0,3 s em cada emenda para o corte não ficar brusco.

O resultado vai para `<nome do vídeo>_corte_sem-pausas-<N>s.mp4`, ao lado do original. O programa lista na tela cada pausa removida e o tempo economizado. Ele considera silêncio tudo abaixo de -30 dB, valor ajustado para gravação de tela com ruído de fundo (constante `LIMITE_SILENCIO_DB` no `cortador.py`, se precisar mexer).

## Transcrever vídeo ou áudio

Serve para reunião gravada (por exemplo com Windows + G), vídeo seu ou qualquer áudio, quando você só quer o **texto**.

1. Coloque o arquivo (vídeo `.mp4`, `.mov`..., ou áudio `.mp3`, `.wav`, `.m4a`...) dentro de `a_cortar/`.
2. Rode `python transcrever.py` e escolha o número do arquivo.
3. O texto aparece na tela conforme é gerado e fica salvo em `<nome do arquivo>_transcricao.txt`, ao lado dele, com o horário de cada frase.

- **Na primeira vez** ele baixa o modelo de reconhecimento de voz (cerca de 460 MB) e depois reaproveita. Um vídeo de 6 minutos leva cerca de 1 minuto no computador.
- O texto pode errar uma palavra ou outra (nomes e termos técnicos principalmente). Serve bem para entender o assunto ou pedir um resumo a uma IA; não serve como legenda final.
- **Não separa quem está falando.** Numa reunião, o texto sai corrido, sem "Fulano disse".
- O idioma fixo é português e o modelo é o `small`; os dois ficam no topo do `transcrever.py` (`IDIOMA` e `MODELO`).

## Rascunhos

A pasta `rascunhos/` guarda código de experimentos, como base para ferramentas futuras. Não é para usar no dia a dia. Hoje tem `corte_por_transcricao.py`, que corta as pausas sem fala usando a transcrição, mais cortes manuais fixos para um vídeo específico.

## O que esperar

- O vídeo original nunca é alterado.
- Cada corte novo gera um arquivo novo (o intervalo vai no nome). Repetir exatamente o mesmo intervalo sobrescreve o arquivo anterior, sem avisar.
- O corte é **reencodado** (o vídeo é regravado) para sair exato no segundo. Por isso demora um pouco; um trecho de 2 minutos leva de segundos a poucos minutos, dependendo do computador.
- Se o fim que você digitar passar da duração do vídeo, o programa avisa e corta até o final dele.

## Limitações desta versão

- Um corte por vez (sem fila de vários trechos de uma vez).
- Não mostra pré-visualização: confira o resultado abrindo o arquivo gerado.
- Os vídeos ficam só na pasta `a_cortar/`, que o Git ignora (vídeos são grandes demais para versionar).
