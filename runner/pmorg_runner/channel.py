"""Canal simulat cu participanți scriptați (02-MVP §4.5, §7.3).

Transportul e simulat; conversația e reală ca model: identitate structurală,
ID extern per mesaj, corelare explicită. Fără LLM: replicile sunt fixture.
"""

import hashlib


class SimulatedChannel:
    def __init__(self, scripts):
        # scripts: {participant_key: [replici în ordine]}
        self.scripts = {k: list(v) for k, v in scripts.items()}
        self.sent = []
        self.received = []
        self._counter = 0

    def _external_id(self, kind):
        self._counter += 1
        return f"sim-{kind}-{self._counter:04d}"

    def send_message(self, participant_key, body, correlation_id, now):
        msg = {
            "external_message_id": self._external_id("out"),
            "to": participant_key,
            "body": body,
            "correlation_id": correlation_id,
            "sent_at": now,
        }
        self.sent.append(msg)
        return msg

    def receive_reply(self, participant_key, correlation_id, now):
        """Livrează următoarea replică scriptată a participantului."""
        script = self.scripts.get(participant_key) or []
        if not script:
            return None  # tăcere — participantul nu răspunde
        body = script.pop(0)
        msg = {
            "external_message_id": self._external_id("in"),
            "verified_sender_identity": participant_key,
            "body": body,
            "correlation_id": correlation_id,
            "received_at": now,
            "content_hash": hashlib.sha256(body.encode()).hexdigest(),
        }
        self.received.append(msg)
        return msg
