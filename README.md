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

## O que esperar

- O vídeo original nunca é alterado.
- Cada corte novo gera um arquivo novo (o intervalo vai no nome). Repetir exatamente o mesmo intervalo sobrescreve o arquivo anterior, sem avisar.
- O corte é **reencodado** (o vídeo é regravado) para sair exato no segundo. Por isso demora um pouco; um trecho de 2 minutos leva de segundos a poucos minutos, dependendo do computador.
- Se o fim que você digitar passar da duração do vídeo, o programa avisa e corta até o final dele.

## Limitações desta versão

- Um corte por vez (sem fila de vários trechos de uma vez).
- Não mostra pré-visualização: confira o resultado abrindo o arquivo gerado.
- Os vídeos ficam só na pasta `a_cortar/`, que o Git ignora (vídeos são grandes demais para versionar).
