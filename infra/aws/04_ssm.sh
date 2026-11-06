#!/usr/bin/env bash
# SecureString parameters /group12/staging/<NAME> (A1 §4.1, IMD-102). Each value is read with read -s
# in the owner's terminal and reaches the AWS CLI on standard input, never as an argument. It is
# never written to a file or printed. An existing parameter is skipped; --overwrite replaces it
# (rotation, docs/secrets.md).
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -f "$here/env.sh" ] || { echo "infra/aws/env.sh is missing: copy env.sh.example and fill it in" >&2; exit 1; }
if grep -vE '^[[:space:]]*(#|$)' "$here/env.sh" | grep -q '<'; then
  echo "infra/aws/env.sh still holds a <placeholder>" >&2
  exit 1
fi
# shellcheck source=env.sh.example
. "$here/env.sh"
if [ "$(aws sts get-caller-identity --query Account --output text)" != "$AWS_ACCOUNT_ID" ]; then
  echo "these credentials are not for account AWS_ACCOUNT_ID of env.sh" >&2
  exit 1
fi

overwrite=no
case "${1:-}" in
  "") ;;
  --overwrite) overwrite=yes ;;
  *) echo "usage: 04_ssm.sh [--overwrite]" >&2; exit 2 ;;
esac
[ -t 0 ] || { echo "run this script in your own terminal: it reads values from the keyboard" >&2; exit 1; }

prefix=/group12/staging

exists() {
  [ "$(aws ssm describe-parameters --parameter-filters "Key=Name,Values=$1" \
    --query 'Parameters[0].Name' --output text)" = "$1" ]
}

# Reads the value from standard input.
put_parameter() {
  python3 -c '
import json, sys
json.dump({"Name": sys.argv[1], "Type": "SecureString", "Value": sys.stdin.read(),
           "Overwrite": sys.argv[2] == "yes"}, sys.stdout)
' "$1" "$overwrite" | aws ssm put-parameter --cli-input-json file:///dev/stdin --query Version --output text >/dev/null
  echo "parameter $1 stored"
}

read_value() {
  read -r -s -p "$1: " value
  echo
  [ -n "$value" ] || { echo "empty value: nothing stored" >&2; exit 1; }
}

name="$prefix/DATABASE_URL"
if exists "$name" && [ "$overwrite" = no ]; then
  echo "parameter $name exists"
else
  endpoint="$(aws rds describe-db-instances --db-instance-identifier "$RDS_INSTANCE_ID" \
    --query 'DBInstances[0].Endpoint.Address' --output text)"
  read_value "RDS master password"
  # printf is a shell builtin, so the password never appears in a process's argument list.
  printf '%s' "$value" | python3 -c '
import sys
from urllib.parse import quote
user, host, db_name = sys.argv[1:]
password = quote(sys.stdin.read(), safe="")
sys.stdout.write(f"postgresql+psycopg://{user}:{password}@{host}:5432/{db_name}?sslmode=require")
' "$RDS_MASTER_USER" "$endpoint" "$RDS_DB_NAME" | put_parameter "$name"
  unset value
fi

keys="GEMINI_API_KEY ORS_API_KEY"
# HS256 mode only (A1 §4.1): a template in JWKS mode does not reference the shared secret.
if grep -q SUPABASE_JWT_SECRET "$here/services/api.staging.json.tmpl"; then
  keys="$keys SUPABASE_JWT_SECRET"
fi

for key in $keys; do
  name="$prefix/$key"
  if exists "$name" && [ "$overwrite" = no ]; then
    echo "parameter $name exists"
    continue
  fi
  read_value "$key"
  printf '%s' "$value" | put_parameter "$name"
  unset value
done
