"""Grava o vídeo de apresentação do site via CDP screencast e monta com ffmpeg."""
import base64, json, os, shutil, subprocess, time
from playwright.sync_api import sync_playwright

DIR = os.path.dirname(os.path.abspath(__file__))
FRAMES = os.path.join(DIR, "frames")
SITE = "http://localhost:8765/"
CENA = "http://localhost:8766/cena.html"
OUT = r"C:\dev\prototipos\recanto\video\apresentacao-recanto.mp4"

SCROLL_JS = """([y, ms]) => new Promise(res => {
  const s = window.scrollY, d = (typeof y === 'string' ? document.querySelector(y).getBoundingClientRect().top + s - 60 : y) - s, t0 = performance.now();
  const ease = t => t < .5 ? 4*t*t*t : 1 - Math.pow(-2*t + 2, 3) / 2;
  (function step(now) { const p = Math.min((now - t0) / ms, 1); window.scrollTo(0, s + d * ease(p)); p < 1 ? requestAnimationFrame(step) : res(); })(t0);
})"""

CAPTION_JS = """(txt) => {
  let c = document.getElementById('__cap');
  if (!c) {
    c = document.createElement('div'); c.id = '__cap';
    c.style.cssText = 'position:fixed;left:50%;bottom:48px;transform:translateX(-50%);z-index:100000;padding:16px 30px;border-radius:999px;background:rgba(13,59,19,.92);color:#fff;font:500 22px Outfit,sans-serif;letter-spacing:.02em;box-shadow:0 10px 40px rgba(0,0,0,.35);transition:opacity .5s,transform .5s;opacity:0;white-space:nowrap;border:1px solid rgba(255,213,79,.5)';
    document.body.appendChild(c);
  }
  c.style.opacity = 0;
  setTimeout(() => { if (!txt) return; c.innerHTML = txt; c.style.opacity = 1; }, txt ? 450 : 0);
}"""


class Recorder:
    """Captura frames com timestamp; frames ficam numerados em ordem global."""
    def __init__(self):
        self.frames = []  # (segmento, arquivo, timestamp)
        self.fim = []     # fim de cada segmento (relógio)
        self.n = 0

    def attach(self, page, w, h):
        cdp = page.context.new_cdp_session(page)
        seg = len(self.fim)  # frames que chegarem atrasados continuam no seu segmento
        def on_frame(ev):
            try:
                cdp.send("Page.screencastFrameAck", {"sessionId": ev["sessionId"]})
            except Exception:
                pass
            path = os.path.join(FRAMES, f"{self.n:06d}.jpg"); self.n += 1
            with open(path, "wb") as f:
                f.write(base64.b64decode(ev["data"]))
            self.frames.append((seg, path, ev["metadata"]["timestamp"]))
        cdp.on("Page.screencastFrame", on_frame)
        cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 92, "maxWidth": w, "maxHeight": h, "everyNthFrame": 1})
        return cdp

    def mark_cut(self):
        """Marca troca de segmento: o próximo frame não herda a pausa entre segmentos."""
        self.fim.append(time.time())


FALAS =json.load(open(os.path.join(DIR, "falas.json")))
FALAS_DIR = os.path.join(DIR, "falas")
MARCAS = []  # (cena, relógio) — início de cada fala


def wait(page, s):
    end = time.time() + s
    while time.time() < end:
        page.wait_for_timeout(50)


def fala(nome):
    """Marca o início da fala da cena; devolve função que segura até ela terminar."""
    t0 = time.time()
    MARCAS.append((nome, t0))
    def segura(page, folga=0.5):
        wait(page, max(t0 + FALAS[nome] + folga - time.time(), 0))
    return segura


def main():
    shutil.rmtree(FRAMES, ignore_errors=True)
    os.makedirs(FRAMES)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    rec = Recorder()

    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")

        # --- Intro ---
        cena = b.new_page(viewport={"width": 1920, "height": 1080})
        cena.goto(CENA, wait_until="networkidle"); cena.wait_for_timeout(800)
        cdp = rec.attach(cena, 1920, 1080)
        wait(cena, 0.3)
        cena.evaluate("show('intro')"); wait(cena, 0.6)
        fala("intro")(cena, 0.8)
        cdp.send("Page.stopScreencast"); rec.mark_cut()

        # --- Desktop ---
        ctx = b.new_context(viewport={"width": 1600, "height": 900}, device_scale_factor=1.2)
        pg = ctx.new_page()
        pg.goto(SITE, wait_until="networkidle")
        pg.wait_for_selector("#preloader.hidden", state="attached"); pg.wait_for_timeout(300)
        pg.evaluate("document.querySelectorAll('.hero-status,.hero-logo,.hero-title,.hero-sub,.hero-btns,.hero-info').forEach(n=>{n.style.animation='none';n.offsetHeight;n.style.animation=''})")
        cdp = rec.attach(pg, 1920, 1080)
        wait(pg, 0.4)
        s = fala("hero"); wait(pg, 1.8)
        pg.evaluate(CAPTION_JS, "Nova abertura com foto dos pratos e status <b>aberto agora</b>"); s(pg)
        pg.evaluate(CAPTION_JS, "")
        s = fala("sobre")
        pg.evaluate(SCROLL_JS, ["#sobre", 1500])
        pg.evaluate(CAPTION_JS, "Logo fixa no topo e menu destacando a seção atual"); s(pg)
        pg.evaluate(CAPTION_JS, "")
        s = fala("cardapio")
        pg.evaluate(SCROLL_JS, ["#cardapio", 1500]); wait(pg, 1.2)
        pg.evaluate(SCROLL_JS, [pg.evaluate("scrollY + 420"), 1400])
        pg.evaluate(CAPTION_JS, "Novo: peça o <b>cardápio completo</b> direto no WhatsApp"); s(pg)
        pg.evaluate(CAPTION_JS, "")
        s = fala("galeria")
        pg.evaluate(SCROLL_JS, ["#galeria", 1600])
        pg.evaluate(CAPTION_JS, "Galeria completa no lugar dos espaços “em breve”"); wait(pg, 1.5)
        pg.hover(".gallery-item >> nth=1"); s(pg, 0.2)
        s = fala("lightbox")
        pg.click(".gallery-item >> nth=1"); wait(pg, 0.4)
        pg.evaluate(CAPTION_JS, "Fotos ampliadas com navegação por setas, teclado e toque"); wait(pg, 1.4)
        pg.click("#lbNext"); wait(pg, 1.3)
        pg.click("#lbNext"); s(pg, 0.6)
        pg.keyboard.press("Escape"); wait(pg, 0.4)
        pg.evaluate(CAPTION_JS, "")
        s = fala("contato")
        pg.evaluate(SCROLL_JS, ["#contato", 1500])
        pg.evaluate(CAPTION_JS, "Dia de hoje em destaque e mapa do endereço corrigido"); s(pg)
        pg.evaluate(CAPTION_JS, "")
        pg.evaluate(SCROLL_JS, [999999, 1500]); wait(pg, 0.6)
        cdp.send("Page.stopScreencast"); rec.mark_cut()
        ctx.close()

        # --- Mobile dentro do celular ---
        cena.evaluate("show('mobile'); document.getElementById('frame').src = 'http://localhost:8765/'")
        cena.wait_for_timeout(3500)
        frame = cena.frame_locator("#frame")
        fr = [f for f in cena.frames if f.url.startswith(SITE)][0]
        cdp = rec.attach(cena, 1920, 1080)
        cena.evaluate("show('mobile')"); wait(cena, 0.6)
        s = fala("mobile"); wait(cena, 0.8)
        fr.evaluate(SCROLL_JS, ["#cardapio", 1800]); wait(cena, 0.3)
        fr.evaluate(SCROLL_JS, ["#galeria", 1800]); wait(cena, 0.3)
        fr.evaluate(SCROLL_JS, [0, 1300])
        frame.locator("#mobileToggle").click(); wait(cena, 1.3)
        frame.locator("#mobileToggle").click(); s(cena, 0.6)
        cdp.send("Page.stopScreencast"); rec.mark_cut()

        # --- Resumo e encerramento ---
        cdp = rec.attach(cena, 1920, 1080)
        cena.evaluate("show('resumo')"); wait(cena, 0.5)
        fala("resumo")(cena, 1.2)
        cena.evaluate("show('outro')"); wait(cena, 0.6)
        fala("outro")(cena, 2.0)
        cdp.send("Page.stopScreencast"); rec.mark_cut()
        b.close()

    # duração de cada frame = até o próximo; cortes não herdam a pausa.
    # Monta sequência fixa de 30 fps (hardlinks), pois o concat infla frames curtos.
    tl = []  # (relógio, início no vídeo, duração)
    seq = os.path.join(DIR, "seq")
    shutil.rmtree(seq, ignore_errors=True); os.makedirs(seq)
    t, k = 0.0, 0
    items = sorted(rec.frames, key=lambda f: (f[0], f[2]))
    for i, (sg, path, ts) in enumerate(items):
        if ts > rec.fim[sg]:
            continue
        nxt = items[i + 1] if i + 1 < len(items) and items[i + 1][0] == sg else None
        fim = nxt[2] if nxt and nxt[2] <= rec.fim[sg] else rec.fim[sg]
        dur = max(fim - ts, 0.001)
        tl.append((ts, t, dur))
        n = round((t + dur) * 30) - round(t * 30); t += dur
        for _ in range(n):
            os.link(path, os.path.join(seq, f"{k:06d}.jpg")); k += 1
    muda = os.path.join(DIR, "muda.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", "30", "-i", os.path.join(seq, "%06d.jpg"),
                    "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0D3B13,fps=30,format=yuv420p",
                    "-c:v", "libx264", "-preset", "slow", "-crf", "20", muda], check=True)

    # relógio da marca -> tempo no vídeo (limitado ao fim do frame, por causa dos cortes)
    def no_video(m):
        cand = [x for x in tl if x[0] <= m]
        ts, ini, dur = cand[-1] if cand else tl[0]
        return ini + min(max(m - ts, 0), dur)

    inputs, filt = [], []
    for k, (nome, m) in enumerate(MARCAS):
        ms = int(no_video(m) * 1000)
        print(f"{nome:9s} {ms/1000:6.2f}s")
        inputs += ["-i", os.path.join(FALAS_DIR, f"{nome}.mp3")]
        filt.append(f"[{k+1}:a]adelay={ms}|{ms},volume=1.0[a{k}]")
    mix = "".join(f"[a{k}]" for k in range(len(MARCAS)))
    filt.append(f"{mix}amix=inputs={len(MARCAS)}:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=11,apad[aout]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", muda, *inputs, "-filter_complex", ";".join(filt),
                    "-map", "0:v", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
                    "-shortest", "-movflags", "+faststart", OUT], check=True)
    print("frames:", len(tl), "duração:", round(t, 2), "->", OUT)


if __name__ == "__main__":
    main()
