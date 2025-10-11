#!/usr/bin/env python3
import boto3
import json
import sys
import os

# Configuration
TARGET_ACCOUNTS = [
    '123456789012',
    '987654321098'  # Replace with your account IDs
]
REGIONS = ['us-east-1', 'us-west-2']  # Replace with your regions
ROLE_NAME = 'AnsibleEC2ReadOnlyRole'
MANAGEMENT_ACCOUNT_ID = 'MANAGEMENT-ACCOUNT-ID'  # Replace with your management account ID

def assume_role(account_id, role_name):
    sts_client = boto3.client('sts')
    role_arn = f'arn:aws:iam::{account_id}:role/{role_name}'
    try:
        response = sts_client.assume_role(
            RoleArn=role_arn,
            RoleSessionName='AnsibleInventorySession'
        )
        return boto3.Session(
            aws_access_key_id=response['Credentials']['AccessKeyId'],
            aws_secret_access_key=response['Credentials']['SecretAccessKey'],
            aws_session_token=response['Credentials']['SessionToken']
        )
    except Exception as e:
        print(f"Failed to assume role for account {account_id}: {e}", file=sys.stderr)
        return None

def get_ec2_instances(session, region):
    if not session:
        return []
    ec2_client = session.client('ec2', region_name=region)
    instances = []
    try:
        paginator = ec2_client.get_paginator('describe_instances')
        for page in paginator.paginate(Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]):
            for reservation in page['Reservations']:
                for instance in reservation['Instances']:
                    tags = {t['Key']: t['Value'] for t in instance.get('Tags', [])}
                    instances.append({
                        'id': instance['InstanceId'],
                        'private_ip': instance.get('PrivateIpAddress', ''),
                        'tags': tags,
                        'region': region
                    })
    except Exception as e:
        print(f"Error fetching instances in {region}: {e}", file=sys.stderr)
    return instances

def main():
    inventory = {
        '_meta': {'hostvars': {}},
        'all': {'hosts': []}
    }
    account_alias_groups = {}

    for account_id in TARGET_ACCOUNTS:
        session = assume_role(account_id, ROLE_NAME)
        for region in REGIONS:
            instances = get_ec2_instances(session, region)
            for instance in instances:
                hostname = instance['private_ip']
                if not hostname:
                    continue  # Skip instances without private IP
                inventory['all']['hosts'].append(hostname)
                inventory['_meta']['hostvars'][hostname] = {
                    'ansible_host': hostname,
                    'ansible_user': 'ec2-user',  # Adjust for your AMI (e.g., 'ubuntu')
                    'instance_id': instance['id'],
                    'aws_region': instance['region'],
                    'account_id': account_id,
                    'tags': instance['tags']
                }
                # Group by AccountAlias
                account_alias = instance['tags'].get('AccountAlias')
                if account_alias:
                    group_name = f'tag_AccountAlias_{account_alias}'
                    if group_name not in account_alias_groups:
                        account_alias_groups[group_name] = {'hosts': []}
                    account_alias_groups[group_name]['hosts'].append(hostname)

    inventory.update(account_alias_groups)
    print(json.dumps(inventory, indent=2))

if __name__ == '__main__':
    main()
