"""Gera uma fala por cena com voz neural e grava a duração de cada uma em falas.json."""
import asyncio, json, os, subprocess
import edge_tts

DIR = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(DIR, "falas")
VOZ = "pt-BR-ThalitaMultilingualNeural"

ROTEIRO = {
    "intro": "Olá! Este é o novo site do Recanto Pizzaria e Choperia, aqui em Taquaritinga. Vem comigo ver o que mudou.",
    "hero": "Logo na abertura, uma foto dos nossos pratos já dá água na boca... e o site avisa, na hora, se a casa está aberta.",
    "sobre": "Conforme você rola, a logo fica fixa no topo, e o menu mostra em que parte do site você está.",
    "cardapio": "No cardápio, tem um botão novo que leva direto pro WhatsApp, pra pedir o cardápio completo, com preços e as promoções do dia.",
    "galeria": "A galeria, que antes estava vazia, agora mostra a casa, a pizza, o chopp gelado e as porções.",
    "lightbox": "É só clicar pra ampliar, e ir passando de uma foto pra outra.",
    "contato": "Na parte de contato, o dia de hoje aparece em destaque, e o mapa mostra o endereço certinho.",
    "mobile": "E no celular, fica tudo na palma da mão. Pedir pelo WhatsApp é um toque só.",
    "resumo": "Além disso, o site ficou mais leve, carrega rapidinho, e ficou mais fácil de usar pra todo mundo.",
    "outro": "Recanto Pizzaria e Choperia. Avenida Paulo Roberto Scandar, mil e dezesseis. De terça a domingo, a partir das seis da tarde. Sua mesa está esperando!",
}


async def main():
    os.makedirs(OUT, exist_ok=True)
    duracoes = {}
    for nome, texto in ROTEIRO.items():
        mp3 = os.path.join(OUT, f"{nome}.mp3")
        await edge_tts.Communicate(texto, VOZ, rate="-4%").save(mp3)
        dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", mp3],
                                   capture_output=True, text=True).stdout)
        duracoes[nome] = round(dur, 3)
        print(f"{nome:9s} {dur:5.2f}s")
    json.dump(duracoes, open(os.path.join(DIR, "falas.json"), "w"), indent=1)


asyncio.run(main())
