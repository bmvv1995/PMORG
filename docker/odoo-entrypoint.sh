#!/bin/bash

set -Eeuo pipefail

template="${ODOO_CONFIG_TEMPLATE:-/etc/odoo/odoo.conf}"
runtime_config="/tmp/odoo.conf"
admin_secret="/run/secrets/odoo_admin_password"
db_secret="/run/secrets/odoo_db_password"

if [[ ! -s "${admin_secret}" || ! -s "${db_secret}" ]]; then
    echo "Missing Odoo secret" >&2
    exit 1
fi

install -m 0600 "${template}" "${runtime_config}"
admin_password="$(tr -d '\r\n' < "${admin_secret}")"

if [[ -z "${admin_password}" ]]; then
    echo "Empty Odoo admin password secret" >&2
    exit 1
fi

printf '\nadmin_passwd = %s\n' "${admin_password}" >> "${runtime_config}"
unset admin_password

# Use libpq runtime variables so the database password never appears in the
# Odoo process arguments or in the Compose environment stored by Docker.
db_password="$(tr -d '\r\n' < "${db_secret}")"
if [[ -z "${db_password}" ]]; then
    echo "Empty database password secret" >&2
    exit 1
fi

export PGHOST="${HOST:-db}"
export PGPORT="${PORT:-5432}"
export PGUSER="${USER:-odoo}"
export PGPASSWORD="${db_password}"
unset db_password

export ODOO_RC="${runtime_config}"

if [[ "${1:-}" == "pmorg-seed" ]]; then
    admin_login_secret="/run/secrets/odoo_admin_login_password"
    if [[ ! -s "${admin_login_secret}" ]]; then
        echo "Missing sandbox admin login secret" >&2
        exit 1
    fi

    /entrypoint.sh odoo \
        --stop-after-init \
        --init=base,project,hr,pmorg_core

    /entrypoint.sh odoo shell --database=pmorg_v2_sb2 --no-http <<'PY'
import re
from pathlib import Path

password = Path(
    "/run/secrets/odoo_admin_login_password"
).read_text(encoding="utf-8").strip()

if not re.fullmatch(r"[0-9a-f]{64}", password):
    raise RuntimeError("invalid sandbox admin password")

env.ref("base.user_admin").sudo().write({
    "login": "sandbox-admin",
    "password": password,
})
env.cr.commit()
PY
    exit 0
fi

exec /entrypoint.sh "$@"
