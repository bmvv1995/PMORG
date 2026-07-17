#!/usr/bin/env python3
"""Seed sintetic pentru evaluarea conductei email (tema 08, L2-email).

Trimite prin SMTP (greenmail) 8 mesaje cu adevăr cunoscut în căsuța
pm@atelier-min.example — canalul autorizat. Expected-urile sunt exportate
pentru scorerul din bridge.
"""

import json
import smtplib
import sys
from email.message import EmailMessage

SMTP = ("127.0.0.1", 3025)
PM = "pm@atelier-min.example"
ANA = "Ana Dobre <ana.dobre@atelier-min.example>"
PAUL = "Paul Rusu <paul.rusu@atelier-min.example>"
VICTOR = "Victor Neagu <victor.neagu@atelier-min.example>"

CASES = []


def send(mid, sender, subject, body, date, html=False, reply_to=None,
         expected=None):
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = PM
    msg["Subject"] = subject
    msg["Date"] = date
    msg["Message-ID"] = f"<{mid}@atelier-min.example>"
    if reply_to:
        msg["In-Reply-To"] = f"<{reply_to}@atelier-min.example>"
        msg["References"] = f"<{reply_to}@atelier-min.example>"
    if html:
        msg.set_content(f"<html><body>{body}</body></html>",
                        subtype="html")
    else:
        msg.set_content(body)
    with smtplib.SMTP(*SMTP) as s:
        s.send_message(msg)
    CASES.append(dict(mid=f"<{mid}@atelier-min.example>",
                      expected=expected or {}))


def main():
    # M1 — angajament simplu, text simplu
    send("m1", VICTOR, "factura decor",
         "Salut, rezolv eu factura de la decor pana joi.\n\nVictor",
         "Mon, 20 Jul 2026 09:00:00 +0300",
         expected=dict(require=["commitment"], forbid=["decision"],
                       due=("commitment", "2026-07-23")))
    # M2 — reply cu citat imbricat: DOAR conținutul nou se extrage
    send("m2", PAUL, "Re: factura decor",
         "Ok, mersi. Eu trimit raportul lunar maine.\n\n"
         "La data de 20.07.2026 09:00, Victor Neagu a scris:\n"
         "> Salut, rezolv eu factura de la decor pana joi.\n> \n> Victor\n",
         "Mon, 20 Jul 2026 10:30:00 +0300", reply_to="m1",
         expected=dict(require=["commitment"], forbid=[],
                       due=("commitment", "2026-07-21"), max_commitments=1))
    # M3 — semnătură + disclaimer: doar observația
    send("m3", ANA, "frigiderul 2",
         "Am observat ca frigiderul 2 face iar zgomot.\n\n--\n"
         "Ana Dobre\nOwner, Atelier Minimal Test SRL\n"
         "Acest mesaj este confidential si se adreseaza exclusiv "
         "destinatarului. Va rugam sa nu distribuiti continutul.\n",
         "Mon, 20 Jul 2026 11:00:00 +0300",
         expected=dict(require=["observation"],
                       forbid=["commitment", "decision"]))
    # M4 — email HTML: decizie
    send("m4", ANA, "program nou",
         "<p>Am decis: de la <b>1 august</b> inchidem lunea.</p>",
         "Mon, 20 Jul 2026 12:00:00 +0300", html=True,
         expected=dict(require=["decision"], forbid=["commitment"]))
    # M5a + M5b — perechea pe fir: întrebare + „Da."
    send("m5a", ANA, "livrare Narcoffee",
         "Victor, confirmi ca livrezi comanda Narcoffee vineri?",
         "Mon, 20 Jul 2026 13:00:00 +0300",
         expected=dict(require=["open_question"], forbid=["commitment"]))
    send("m5b", VICTOR, "Re: livrare Narcoffee",
         "Da.",
         "Mon, 20 Jul 2026 13:20:00 +0300", reply_to="m5a",
         expected=dict(require=["commitment"], forbid=[],
                       due=("commitment", "2026-07-24"),
                       author_must_be="victor.neagu@atelier-min.example"))
    # M6 — colocvial fără diacritice
    send("m6", VICTOR, "inventar",
         "am uitat sa zic, poimaine termin inventarul la bar",
         "Mon, 20 Jul 2026 14:00:00 +0300",
         expected=dict(require=["commitment"],
                       due=("commitment", "2026-07-22")))
    # M7 — expeditor NEmapat (identitate necunoscută) => carantină
    send("m7", "Promo SRL <oferte@promo-extern.example>", "Oferta luna iulie",
         "Reducere 50% la toate produsele! Comandati acum!",
         "Mon, 20 Jul 2026 15:00:00 +0300",
         expected=dict(quarantine=True))
    # M8 — termen din denylist-ul de intimitate => refuz fără conținut
    send("m8", ANA, "acces",
         "Apropo, parola de la server e Delta1234, sa o ai.",
         "Mon, 20 Jul 2026 16:00:00 +0300",
         expected=dict(privacy_blocked=True))

    json.dump(CASES, sys.stdout, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
