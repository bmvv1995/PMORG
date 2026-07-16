import secrets
from datetime import datetime, timedelta

from odoo import _, api, fields, models

CONTRACT_VERSION = "1.0"
DEFAULT_LEASE_SECONDS = 300
MAX_LEASE_SECONDS = 3600

ENVELOPE_KEYS = {"schema_version", "message_id", "actor", "occurred_at"}
READ_ONLY_COMMANDS = {"list_due_work", "get_task_state", "list_outbox"}


class ApiError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


class PmorgOrchestratorApi(models.AbstractModel):
    """Suprafața de comenzi pentru runtime (06-CONTRACTS v1.0).

    Fail-closed: orice altă scriere a runtime-ului în Odoo nu există.
    """

    _name = "pmorg.orchestrator.api"
    _description = "API orchestrator PMORG"

    # ------------------------------------------------------------------ utils

    @api.model
    def _parse_dt(self, value, field_name="datetime"):
        if isinstance(value, datetime):
            return value
        if not value or not isinstance(value, str):
            raise ApiError("E_SCHEMA", f"Câmp datetime invalid: {field_name}.")
        try:
            raw = value.replace("Z", "+00:00").replace("T", " ")
            dt = datetime.fromisoformat(raw)
            if dt.tzinfo:
                dt = dt.astimezone(tz=None).replace(tzinfo=None)
            return dt
        except ValueError as exc:
            raise ApiError(
                "E_SCHEMA", f"Câmp datetime neparsabil ({field_name}): {value}"
            ) from exc

    @api.model
    def _validate_envelope(self, payload, mutant):
        if not isinstance(payload, dict):
            raise ApiError("E_SCHEMA", "Payload-ul trebuie să fie obiect JSON.")
        missing = ENVELOPE_KEYS - payload.keys()
        if missing:
            raise ApiError("E_SCHEMA", f"Câmpuri de anvelopă lipsă: {sorted(missing)}.")
        major = str(payload["schema_version"]).split(".")[0]
        if major != CONTRACT_VERSION.split(".")[0]:
            raise ApiError(
                "E_SCHEMA",
                f"Versiune de contract incompatibilă: {payload['schema_version']}.",
            )
        actor = payload.get("actor") or {}
        if not isinstance(actor, dict) or not actor.get("id"):
            raise ApiError("E_AUTH", "Actor lipsă sau fără identitate.")
        if mutant and not payload.get("idempotency_key"):
            raise ApiError(
                "E_SCHEMA", "idempotency_key este obligatoriu la comenzi mutante."
            )

    @api.model
    def _get_task(self, params):
        task_id = params.get("task_id")
        if not task_id:
            raise ApiError("E_SCHEMA", "task_id lipsă.")
        task = self.env["project.task"].browse(int(task_id))
        if not task.exists():
            raise ApiError("E_UNKNOWN", f"Task inexistent: {task_id}.")
        return task

    @api.model
    def _get_run(self, task, params, now):
        run_id = params.get("run_id")
        token = params.get("lease_token")
        if not run_id or not token:
            raise ApiError("E_SCHEMA", "run_id și lease_token sunt obligatorii.")
        run = self.env["pmorg.task.run"].browse(int(run_id))
        if not run.exists() or run.task_id != task:
            raise ApiError("E_UNKNOWN", f"Run inexistent pe task: {run_id}.")
        if run.lease_token != token or not run.is_lease_valid(now):
            raise ApiError("E_LEASE", "Lease invalid sau expirat.")
        return run

    @api.model
    def _check_version(self, task, params):
        expected = params.get("expected_version")
        if expected is not None and int(expected) != task.state_version:
            raise ApiError(
                "E_VERSION",
                f"Versiune așteptată {expected}, curentă {task.state_version}.",
            )

    @api.model
    def _transition(self, task, new_state, event_type, envelope, run=None, extra=None):
        task.write(
            dict(
                {"orchestration_state": new_state,
                 "state_version": task.state_version + 1},
                **(extra or {}),
            )
        )
        self._emit(task, event_type, envelope, run=run)

    @api.model
    def _emit(self, task, event_type, envelope, run=None, data=None):
        actor = (envelope.get("actor") or {}).get("id")
        payload = {
            "correlation_id": envelope.get("correlation_id"),
            "causation_id": envelope.get("message_id"),
            "task_id": task.id,
            "run_id": run.id if run else None,
            "state_version": task.state_version,
            "data": data or {},
        }
        self.env["pmorg.task.event"].create(
            {
                "task_id": task.id,
                "run_id": run.id if run else False,
                "event_type": event_type,
                "actor_id": actor,
                "payload": payload,
            }
        )
        self.env["pmorg.outbox.event"].create(
            {
                "message_id": secrets.token_hex(16),
                "event_type": event_type,
                "payload": dict(payload, actor_id=actor),
            }
        )

    # -------------------------------------------------------------- dispatch

    @api.model
    def _dispatch(self, command, payload):
        mutant = command not in READ_ONLY_COMMANDS
        try:
            self._validate_envelope(payload, mutant)
        except ApiError as exc:
            return {
                "status": "error",
                "error": {"code": exc.code, "message": exc.message},
                "message_id": isinstance(payload, dict)
                and payload.get("message_id")
                or None,
            }

        actor_id = payload["actor"]["id"]
        key = payload.get("idempotency_key")
        Inbox = self.env["pmorg.command.inbox"]

        if mutant:
            prior = Inbox.search(
                [("actor_id", "=", actor_id), ("idempotency_key", "=", key)], limit=1
            )
            if prior:
                response = dict(prior.response or {})
                response["status"] = "replay"
                response["message_id"] = payload.get("message_id")
                return response

        handler = getattr(self, f"_cmd_{command}", None)
        if handler is None:
            response = {
                "status": "error",
                "error": {"code": "E_SCHEMA", "message": f"Comandă necunoscută: {command}"},
            }
        else:
            try:
                with self.env.cr.savepoint():
                    result = handler(payload, payload.get("params") or {})
                response = {"status": "ok", "result": result}
            except ApiError as exc:
                response = {
                    "status": "error",
                    "error": {"code": exc.code, "message": exc.message},
                }

        response["message_id"] = payload.get("message_id")
        if mutant:
            Inbox.create(
                {
                    "actor_id": actor_id,
                    "idempotency_key": key,
                    "command": command,
                    "response": response,
                }
            )
        return response

    # ------------------------------------------------------------- read-only

    def _cmd_list_due_work(self, envelope, params):
        now = self._parse_dt(params.get("now") or envelope["occurred_at"], "now")
        limit = int(params.get("limit") or 50)
        domain = [
            "|",
            ("orchestration_state", "=", "ready"),
            "&",
            ("orchestration_state", "=", "scheduled"),
            ("next_check_at", "<=", now),
        ]
        if params.get("initiative_id"):
            domain = [
                ("pmorg_initiative_id", "=", int(params["initiative_id"]))
            ] + domain
        if params.get("execution_mode"):
            domain = [("execution_mode", "=", params["execution_mode"])] + domain
        tasks = self.env["project.task"].search(
            domain, limit=limit, order="next_check_at asc nulls first, id asc"
        )
        return {
            "now": params.get("now") or envelope["occurred_at"],
            "tasks": [
                {
                    "task_id": t.id,
                    "name": t.name,
                    "pmorg_task_type": t.pmorg_task_type,
                    "execution_mode": t.execution_mode,
                    "orchestration_state": t.orchestration_state,
                    "next_check_at": fields.Datetime.to_string(t.next_check_at)
                    if t.next_check_at
                    else None,
                    "state_version": t.state_version,
                    "initiative_id": t.pmorg_initiative_id.id or None,
                }
                for t in tasks
            ],
        }

    def _cmd_get_task_state(self, envelope, params):
        task = self._get_task(params)
        run = self.env["pmorg.task.run"].search(
            [("task_id", "=", task.id), ("outcome", "=", "running")], limit=1
        )
        return {
            "task_id": task.id,
            "orchestration_state": task.orchestration_state,
            "state_version": task.state_version,
            "verification_status": task.verification_status,
            "next_check_at": fields.Datetime.to_string(task.next_check_at)
            if task.next_check_at
            else None,
            "active_run": {
                "run_id": run.id,
                "actor_id": run.actor_id,
                "lease_expires_at": fields.Datetime.to_string(run.lease_expires_at),
            }
            if run
            else None,
        }

    def _cmd_list_outbox(self, envelope, params):
        after = int(params.get("after_id") or 0)
        limit = int(params.get("limit") or 100)
        events = self.env["pmorg.outbox.event"].search(
            [("id", ">", after)], limit=limit, order="id asc"
        )
        return {
            "events": [
                {
                    "id": e.id,
                    "message_id": e.message_id,
                    "event_type": e.event_type,
                    "payload": e.payload,
                }
                for e in events
            ]
        }

    # --------------------------------------------------------------- mutante

    def _cmd_mark_managed(self, envelope, params):
        task = self._get_task(params)
        if task.orchestration_state != "not_managed":
            raise ApiError(
                "E_STATE", f"Tranziție invalidă din {task.orchestration_state}."
            )
        self._transition(task, "ready", "task.ready", envelope)
        return {"task_id": task.id, "state_version": task.state_version}

    def _cmd_claim_task(self, envelope, params):
        task = self._get_task(params)
        now = self._parse_dt(params.get("now") or envelope["occurred_at"], "now")
        company_id = envelope.get("company_id")
        if company_id and task.company_id.id != int(company_id):
            raise ApiError("E_COMPANY", "Compania nu corespunde taskului.")

        # Row lock: serializează claim-urile concurente pe același task.
        self.env.cr.execute(
            "SELECT id FROM project_task WHERE id = %s FOR UPDATE", (task.id,)
        )
        task.invalidate_recordset()

        self._check_version(task, params)

        active = self.env["pmorg.task.run"].search(
            [("task_id", "=", task.id), ("outcome", "=", "running")], limit=1
        )
        if active and active.is_lease_valid(now):
            raise ApiError("E_LEASE_HELD", "Există un lease valid al altui owner.")
        if active:
            self._fail_expired_run(active, envelope, now)

        state = task.orchestration_state
        if state == "scheduled":
            if task.next_check_at and task.next_check_at > now:
                raise ApiError("E_NOT_DUE", "Taskul programat nu este încă scadent.")
        elif state != "ready":
            raise ApiError("E_STATE", f"Taskul nu poate fi revendicat din {state}.")

        lease_seconds = min(
            int(params.get("lease_seconds") or DEFAULT_LEASE_SECONDS),
            MAX_LEASE_SECONDS,
        )
        run = self.env["pmorg.task.run"].create(
            {
                "task_id": task.id,
                "actor_type": envelope["actor"].get("type") or "agent",
                "actor_id": envelope["actor"]["id"],
                "started_at": now,
                "lease_token": secrets.token_urlsafe(24),
                "lease_expires_at": now + timedelta(seconds=lease_seconds),
            }
        )
        self._transition(
            task,
            "claimed",
            "task.claimed",
            envelope,
            run=run,
            extra={"active_run_id": str(run.id)},
        )
        return {
            "task_id": task.id,
            "run_id": run.id,
            "lease_token": run.lease_token,
            "lease_expires_at": fields.Datetime.to_string(run.lease_expires_at),
            "state_version": task.state_version,
        }

    def _cmd_heartbeat(self, envelope, params):
        task = self._get_task(params)
        now = self._parse_dt(params.get("now") or envelope["occurred_at"], "now")
        run = self._get_run(task, params, now)
        extend = min(
            int(params.get("extend_seconds") or DEFAULT_LEASE_SECONDS),
            MAX_LEASE_SECONDS,
        )
        run.lease_expires_at = now + timedelta(seconds=extend)
        return {
            "run_id": run.id,
            "lease_expires_at": fields.Datetime.to_string(run.lease_expires_at),
        }

    def _cmd_record_progress(self, envelope, params):
        task = self._get_task(params)
        now = self._parse_dt(params.get("now") or envelope["occurred_at"], "now")
        run = self._get_run(task, params, now)
        if task.orchestration_state not in ("claimed", "running", "waiting_response"):
            raise ApiError(
                "E_STATE", f"Progres imposibil din {task.orchestration_state}."
            )
        self._transition(
            task,
            "running",
            "task.progress",
            envelope,
            run=run,
            extra={"last_progress_at": now},
        )
        return {"task_id": task.id, "state_version": task.state_version}

    def _cmd_record_waiting_response(self, envelope, params):
        task = self._get_task(params)
        now = self._parse_dt(params.get("now") or envelope["occurred_at"], "now")
        run = self._get_run(task, params, now)
        if task.orchestration_state not in ("claimed", "running"):
            raise ApiError(
                "E_STATE", f"Tranziție invalidă din {task.orchestration_state}."
            )
        partner_id = params.get("awaiting_partner_id")
        if not partner_id:
            raise ApiError("E_SCHEMA", "awaiting_partner_id lipsă.")
        self._transition(
            task,
            "waiting_response",
            "task.waiting_response",
            envelope,
            run=run,
            extra={
                "awaiting_response_from": int(partner_id),
                "awaiting_since": now,
            },
        )
        return {"task_id": task.id, "state_version": task.state_version}

    def _cmd_schedule_next_check(self, envelope, params):
        task = self._get_task(params)
        now = self._parse_dt(params.get("now") or envelope["occurred_at"], "now")
        run = self._get_run(task, params, now)
        next_check = self._parse_dt(params.get("next_check_at"), "next_check_at")
        run.write({"outcome": "released", "ended_at": now,
                   "summary": params.get("reason") or "scheduled"})
        self._transition(
            task,
            "scheduled",
            "task.scheduled",
            envelope,
            run=run,
            extra={"next_check_at": next_check, "active_run_id": False},
        )
        return {"task_id": task.id, "state_version": task.state_version}

    def _cmd_block_task(self, envelope, params):
        task = self._get_task(params)
        now = self._parse_dt(params.get("now") or envelope["occurred_at"], "now")
        run = self._get_run(task, params, now)
        if not params.get("reason"):
            raise ApiError("E_SCHEMA", "Blocarea cere un motiv explicit.")
        run.write({"outcome": "released", "ended_at": now,
                   "summary": f"blocked: {params['reason']}"})
        self._transition(
            task,
            "blocked",
            "task.blocked",
            envelope,
            run=run,
            extra={"active_run_id": False},
        )
        return {"task_id": task.id, "state_version": task.state_version}

    def _cmd_release_task(self, envelope, params):
        task = self._get_task(params)
        now = self._parse_dt(params.get("now") or envelope["occurred_at"], "now")
        if task.orchestration_state == "blocked":
            if params.get("reason") != "unblocked":
                raise ApiError("E_SCHEMA", "Deblocarea cere reason='unblocked'.")
            self._transition(task, "ready", "task.released", envelope)
            return {"task_id": task.id, "state_version": task.state_version}
        run = self._get_run(task, params, now)
        run.write({"outcome": "released", "ended_at": now,
                   "summary": params.get("reason") or "released"})
        self._transition(
            task,
            "ready",
            "task.released",
            envelope,
            run=run,
            extra={"active_run_id": False},
        )
        return {"task_id": task.id, "state_version": task.state_version}

    def _cmd_complete_run(self, envelope, params):
        task = self._get_task(params)
        now = self._parse_dt(params.get("now") or envelope["occurred_at"], "now")
        run = self._get_run(task, params, now)
        outcome = params.get("outcome")
        if outcome not in ("done", "failed", "needs_review"):
            raise ApiError("E_SCHEMA", f"Outcome invalid: {outcome}.")
        if outcome == "done":
            if not params.get("summary"):
                raise ApiError("E_CRITERIA", "Finalizarea cere un rezumat.")
            if task.completion_criteria and not params.get("evidence_refs"):
                raise ApiError(
                    "E_CRITERIA",
                    "Taskul are criterii de completare: evidence_refs obligatoriu.",
                )
        state_map = {
            "done": "completed",
            "failed": "failed",
            "needs_review": "review",
        }
        run.write(
            {
                "outcome": "done" if outcome == "done" else
                ("failed" if outcome == "failed" else "needs_review"),
                "ended_at": now,
                "summary": params.get("summary") or "",
                "failure_reason": params.get("failure_reason") or "",
            }
        )
        event = {
            "done": "task.run_completed",
            "failed": "task.run_failed",
            "needs_review": "task.run_completed",
        }[outcome]
        self._transition(
            task,
            state_map[outcome],
            event,
            envelope,
            run=run,
            extra={"active_run_id": False},
        )
        for ref in params.get("evidence_refs") or []:
            self._emit(task, "task.evidence_reference", envelope, run=run,
                       data={"memory_ref": ref})
        return {
            "task_id": task.id,
            "run_id": run.id,
            "orchestration_state": task.orchestration_state,
            "state_version": task.state_version,
        }

    def _cmd_record_evidence_reference(self, envelope, params):
        task = self._get_task(params)
        if not params.get("memory_ref"):
            raise ApiError("E_SCHEMA", "memory_ref lipsă.")
        self._emit(
            task,
            "task.evidence_reference",
            envelope,
            data={
                "memory_ref": params["memory_ref"],
                "kind": params.get("kind") or "evidence",
                "note": params.get("note") or "",
            },
        )
        return {"task_id": task.id}

    def _cmd_propose_task(self, envelope, params):
        initiative_id = params.get("initiative_id")
        if not initiative_id or not params.get("name"):
            raise ApiError("E_SCHEMA", "initiative_id și name sunt obligatorii.")
        initiative = self.env["pmorg.initiative"].browse(int(initiative_id))
        if not initiative.exists():
            raise ApiError("E_UNKNOWN", f"Inițiativă inexistentă: {initiative_id}.")
        if not initiative.project_id:
            raise ApiError("E_STATE", "Inițiativa nu are proiect asociat.")
        task = self.env["project.task"].create(
            {
                "name": params["name"],
                "project_id": initiative.project_id.id,
                "pmorg_initiative_id": initiative.id,
                "pmorg_task_type": params.get("pmorg_task_type") or "execution",
                "execution_mode": params.get("execution_mode") or "human",
                "expected_outcome": params.get("expected_outcome") or False,
                "orchestration_state": "ready",
                "participant_ids": [
                    (4, int(pid)) for pid in params.get("participant_ids") or []
                ],
            }
        )
        self._emit(task, "task.ready", envelope, data={"proposed": True})
        return {"task_id": task.id, "state_version": task.state_version}

    def _cmd_record_confirmation(self, envelope, params):
        task = self._get_task(params)
        if not params.get("confirmed_by_partner_id"):
            raise ApiError("E_SCHEMA", "confirmed_by_partner_id lipsă.")
        self._emit(
            task,
            "task.confirmation",
            envelope,
            data={
                "confirmed_by_partner_id": int(params["confirmed_by_partner_id"]),
                "note": params.get("note") or "",
            },
        )
        return {"task_id": task.id}

    def _cmd_request_approval(self, envelope, params):
        task = self._get_task(params)
        now = self._parse_dt(params.get("now") or envelope["occurred_at"], "now")
        run = self._get_run(task, params, now)
        if not params.get("subject"):
            raise ApiError("E_SCHEMA", "subject lipsă.")
        self._transition(
            task,
            "waiting_approval",
            "task.approval_requested",
            envelope,
            run=run,
        )
        self._emit(task, "task.approval_details", envelope, run=run,
                   data={"subject": params["subject"],
                         "details": params.get("details") or ""})
        return {"task_id": task.id, "state_version": task.state_version}

    def _cmd_request_outcome_verification(self, envelope, params):
        task = self._get_task(params)
        if not params.get("evidence_refs"):
            raise ApiError("E_CRITERIA", "Verificarea cere evidence_refs.")
        task.write({"verification_status": "pending",
                    "state_version": task.state_version + 1})
        self._emit(
            task,
            "task.verification_requested",
            envelope,
            data={"evidence_refs": params["evidence_refs"]},
        )
        return {"task_id": task.id, "verification_status": "pending"}

    def _cmd_reclaim_expired(self, envelope, params):
        now = self._parse_dt(params.get("now") or envelope["occurred_at"], "now")
        expired = self.env["pmorg.task.run"].search(
            [("outcome", "=", "running"), ("lease_expires_at", "<", now)]
        )
        reclaimed = []
        for run in expired:
            self._fail_expired_run(run, envelope, now)
            reclaimed.append(run.id)
        return {"reclaimed_run_ids": reclaimed}

    def _fail_expired_run(self, run, envelope, now):
        task = run.task_id
        run.write(
            {"outcome": "failed", "ended_at": now, "failure_reason": "lease_expired"}
        )
        self._transition(
            task,
            "ready",
            "task.lease_expired",
            envelope,
            run=run,
            extra={"active_run_id": False},
        )

    def _cmd_execute_authorized_command(self, envelope, params):
        raise ApiError(
            "E_AUTONOMY",
            "Nicio comandă de business nu este autorizată încă (fail-closed, v1.0).",
        )

    # ------------------------------------------------------------ public API

    @api.model
    def _sanitize(self, value):
        """XML-RPC nu serializează None: îl înlocuim cu False la graniță."""
        if value is None:
            return False
        if isinstance(value, dict):
            return {k: self._sanitize(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [self._sanitize(v) for v in value]
        return value

    @api.model
    def api_call(self, command, payload):
        """Punct unic de intrare pentru runtime (execute_kw)."""
        return self._sanitize(self._dispatch(command, payload))
