#!/usr/bin/env bash
# Private RDS PostgreSQL 16 and its security group (A1 §4.1, §5.1; IMD-100). The group starts with no
# inbound rule; 06_services.sh adds TCP 5432 from the API service's group. The master password is
# set here by the owner and is not RDS-managed, so DATABASE_URL does not go stale.
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

vpc_id="$(aws ec2 describe-vpcs --filters Name=is-default,Values=true --query 'Vpcs[0].VpcId' --output text)"
if [ "$vpc_id" = "None" ]; then
  echo "this region has no default VPC; stop and ask for a decision (IMD-104)" >&2
  exit 1
fi

sg_id="$(aws ec2 describe-security-groups \
  --filters "Name=group-name,Values=$RDS_SECURITY_GROUP" "Name=vpc-id,Values=$vpc_id" \
  --query 'SecurityGroups[0].GroupId' --output text)"
if [ "$sg_id" = "None" ]; then
  sg_id="$(aws ec2 create-security-group --group-name "$RDS_SECURITY_GROUP" \
    --description "group12 RDS: TCP 5432 from the API service only" --vpc-id "$vpc_id" \
    --query GroupId --output text)"
  echo "security group $RDS_SECURITY_GROUP created: $sg_id"
else
  echo "security group $RDS_SECURITY_GROUP exists: $sg_id"
fi

if aws rds describe-db-instances --db-instance-identifier "$RDS_INSTANCE_ID" \
  --query 'DBInstances[0].DBInstanceArn' --output text 2>/dev/null; then
  echo "database instance $RDS_INSTANCE_ID exists"
  exit 0
fi

engine_version="$(aws rds describe-db-engine-versions --engine postgres \
  --query "DBEngineVersions[?starts_with(EngineVersion, '16.')].EngineVersion" --output text \
  | tr '\t' '\n' | sort -V | tail -n 1)"
[ -n "$engine_version" ] || { echo "no PostgreSQL 16 engine version found" >&2; exit 1; }

[ -t 0 ] || { echo "run this script in your own terminal: it reads the password from the keyboard" >&2; exit 1; }
read -r -s -p "New RDS master password: " password
echo
read -r -s -p "Repeat the password: " repeated
echo
[ -n "$password" ] && [ "$password" = "$repeated" ] || { echo "the passwords are empty or differ" >&2; exit 1; }
unset repeated

# The password goes through standard input only; printf is a shell builtin, so it never appears in
# a process's argument list.
printf '%s' "$password" | python3 -c '
import json, sys
instance, db_class, version, user, db_name, group = sys.argv[1:]
json.dump({
    "DBInstanceIdentifier": instance,
    "DBInstanceClass": db_class,
    "Engine": "postgres",
    "EngineVersion": version,
    "MasterUsername": user,
    "MasterUserPassword": sys.stdin.read(),
    "DBName": db_name,
    "AllocatedStorage": 20,
    "StorageType": "gp3",
    "MultiAZ": False,
    "PubliclyAccessible": False,
    "BackupRetentionPeriod": 1,
    "DeletionProtection": True,
    "VpcSecurityGroupIds": [group],
}, sys.stdout)
' "$RDS_INSTANCE_ID" "$RDS_INSTANCE_CLASS" "$engine_version" "$RDS_MASTER_USER" "$RDS_DB_NAME" "$sg_id" \
  | aws rds create-db-instance --cli-input-json file:///dev/stdin \
    --query 'DBInstance.DBInstanceArn' --output text
unset password

echo "waiting for $RDS_INSTANCE_ID (PostgreSQL $engine_version) to become available"
aws rds wait db-instance-available --db-instance-identifier "$RDS_INSTANCE_ID"
echo "database instance $RDS_INSTANCE_ID available"
