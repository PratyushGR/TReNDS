import json
import os
import boto3
import time
import csv
import re
import itertools 
#from itertools import chain, izip_longest

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from datetime import datetime, timedelta
from pprint import pprint


boto3=boto3.session.Session()
IAM_CLIENT=boto3.client('iam')
client = boto3.client('ec2')

# 1.1 Avoid the use of the "root" account (Scored)
def control_1_1_root_use(credreport):
    """Summary
    Args:
        credreport (TYPE): Description
    Returns:
        TYPE: Description
    """
    result = True
    failReason = ""
    offenders = []
    control = "1.1"
    description = "Avoid the use of the root account"
    scored = True
    if "Fail" in credreport:  # Report failure in control
        sys.exit(credreport)
    # Check if root is used in the last 24h
    now = time.strftime('%Y-%m-%dT%H:%M:%S+00:00', time.gmtime(time.time()))
    frm = "%Y-%m-%dT%H:%M:%S+00:00"

    try:
        pwdDelta = (datetime.strptime(now, frm) - datetime.strptime(credreport[0]['password_last_used'], frm))
        if (pwdDelta.days == CONTROL_1_1_DAYS) & (pwdDelta.seconds > 0):  # Used within last 24h
            failReason = "Used within 24h"
            result = False
    except:
        if credreport[0]['password_last_used'] == "N/A" or "no_information":
            pass
        else:
            print("Something went wrong")

    try:
        key1Delta = (datetime.strptime(now, frm) - datetime.strptime(credreport[0]['access_key_1_last_used_date'], frm))
        if (key1Delta.days == CONTROL_1_1_DAYS) & (key1Delta.seconds > 0):  # Used within last 24h
            failReason = "Used within 24h"
            result = False
    except:
        if credreport[0]['access_key_1_last_used_date'] == "N/A" or "no_information":
            pass
        else:
            print("Something went wrong")
    try:
        key2Delta = datetime.strptime(now, frm) - datetime.strptime(credreport[0]['access_key_2_last_used_date'], frm)
        if (key2Delta.days == CONTROL_1_1_DAYS) & (key2Delta.seconds > 0):  # Used within last 24h
            failReason = "Used within 24h"
            result = False
    except:
        if credreport[0]['access_key_2_last_used_date'] == "N/A" or "no_information":
            pass
        else:
            print("Something went wrong")
    print({'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control})
    return {'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control}


# 1.2 Ensure multi-factor authentication (MFA) is enabled for all IAM users that have a console password (Scored)
def control_1_2_mfa_on_password_enabled_iam(credreport):
    """Summary
    Args:
        credreport (TYPE): Description
    Returns:
        TYPE: Description
    """
    result = True
    failReason = ""
    offenders = []
    control = "1.2"
    description = "Ensure multi-factor authentication (MFA) is enabled for all IAM users that have a console password"
    scored = True
    for i in range(len(credreport)):
        # Verify if the user have a password configured
        if credreport[i]['password_enabled'] == "true":
            # Verify if password users have MFA assigned
            if credreport[i]['mfa_active'] == "false":
                result = False
                failReason = "No MFA on users with password. "
                offenders.append(str(credreport[i]['arn']))
    print({'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control})
    return {'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control}


# 1.3 Ensure credentials unused for 90 days or greater are disabled (Scored)
def control_1_3_unused_credentials(credreport):
    """Summary
    Args:
        credreport (TYPE): Description
    Returns:
        TYPE: Description
    """
    result = True
    failReason = ""
    offenders = []
    control = "1.3"
    description = "Ensure credentials unused for 90 days or greater are disabled"
    scored = True
    # Get current time
    now = time.strftime('%Y-%m-%dT%H:%M:%S+00:00', time.gmtime(time.time()))
    frm = "%Y-%m-%dT%H:%M:%S+00:00"

    # Look for unused credentails
    for i in range(len(credreport)):
        if credreport[i]['password_enabled'] == "true":
            try:
                delta = datetime.strptime(now, frm) - datetime.strptime(credreport[i]['password_last_used'], frm)
                # Verify password have been used in the last 90 days
                if delta.days > 90:
                    result = False
                    failReason = "Credentials unused > 90 days detected. "
                    offenders.append(str(credreport[i]['arn']) + ":password")
            except:
                pass  # Never used
        if credreport[i]['access_key_1_active'] == "true":
            try:
                delta = datetime.strptime(now, frm) - datetime.strptime(credreport[i]['access_key_1_last_used_date'], frm)
                # Verify password have been used in the last 90 days
                if delta.days > 90:
                    result = False
                    failReason = "Credentials unused > 90 days detected. "
                    offenders.append(str(credreport[i]['arn']) + ":key1")
            except:
                pass
        if credreport[i]['access_key_2_active'] == "true":
            try:
                delta = datetime.strptime(now, frm) - datetime.strptime(credreport[i]['access_key_2_last_used_date'], frm)
                # Verify password have been used in the last 90 days
                if delta.days > 90:
                    result = False
                    failReason = "Credentials unused > 90 days detected. "
                    offenders.append(str(credreport[i]['arn']) + ":key2")
            except:
                # Never used
                pass
    print( {'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control})
    return {'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control}


# 1.4 Ensure access keys are rotated every 90 days or less (Scored)
def control_1_4_rotated_keys(credreport):
    """Summary
    Args:
        credreport (TYPE): Description
    Returns:
        TYPE: Description
    """
    result = True
    failReason = ""
    offenders = []
    control = "1.4"
    description = "Ensure access keys are rotated every 90 days or less"
    scored = True
    # Get current time
    now = time.strftime('%Y-%m-%dT%H:%M:%S+00:00', time.gmtime(time.time()))
    frm = "%Y-%m-%dT%H:%M:%S+00:00"

    # Look for unused credentails
    for i in range(len(credreport)):
        if credreport[i]['access_key_1_active'] == "true":
            try:
                delta = datetime.strptime(now, frm) - datetime.strptime(credreport[i]['access_key_1_last_rotated'], frm)
                # Verify keys have rotated in the last 90 days
                if delta.days > 90:
                    result = False
                    failReason = "Key rotation >90 days or not used since rotation"
                    offenders.append(str(credreport[i]['arn']) + ":unrotated key1")
            except:
                pass
            try:
                last_used_datetime = datetime.strptime(credreport[i]['access_key_1_last_used_date'], frm)
                last_rotated_datetime = datetime.strptime(credreport[i]['access_key_1_last_rotated'], frm)
                # Verify keys have been used since rotation.
                if last_used_datetime < last_rotated_datetime:
                    result = False
                    failReason = "Key rotation >90 days or not used since rotation"
                    offenders.append(str(credreport[i]['arn']) + ":unused key1")
            except:
                pass
        if credreport[i]['access_key_2_active'] == "true":
            try:
                delta = datetime.strptime(now, frm) - datetime.strptime(credreport[i]['access_key_2_last_rotated'], frm)
                # Verify keys have rotated in the last 90 days
                if delta.days > 90:
                    result = False
                    failReason = "Key rotation >90 days or not used since rotation"
                    offenders.append(str(credreport[i]['arn']) + ":unrotated key2")
            except:
                pass
            try:
                last_used_datetime = datetime.strptime(credreport[i]['access_key_2_last_used_date'], frm)
                last_rotated_datetime = datetime.strptime(credreport[i]['access_key_2_last_rotated'], frm)
                # Verify keys have been used since rotation.
                if last_used_datetime < last_rotated_datetime:
                    result = False
                    failReason = "Key rotation >90 days or not used since rotation"
                    offenders.append(str(credreport[i]['arn']) + ":unused key2")
            except:
                pass
    print({'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control})
    return {'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control}

# 1.5 Ensure IAM password policy requires at least one uppercase letter (Scored)
def control_1_5_password_policy_uppercase(passwordpolicy):
    """Summary
    Args:
        passwordpolicy (TYPE): Description
    Returns:
        TYPE: Description
    """
    result = True
    failReason = ""
    offenders = []
    control = "1.5"
    description = "Ensure IAM password policy requires at least one uppercase letter"
    scored = True
    if passwordpolicy is False:
        result = False
        failReason = "Account does not have a IAM password policy."
    else:
        if passwordpolicy['RequireUppercaseCharacters'] is False:
            result = False
            failReason = "Password policy does not require at least one uppercase letter"
    print({'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control})
    return {'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control}



# 1.6 Ensure IAM password policy requires at least one lowercase letter (Scored)
def control_1_6_password_policy_lowercase(passwordpolicy):
    """Summary
    Args:
        passwordpolicy (TYPE): Description
    Returns:
        TYPE: Description
    """
    result = True
    failReason = ""
    offenders = []
    control = "1.6"
    description = "Ensure IAM password policy requires at least one lowercase letter"
    scored = True
    if passwordpolicy is False:
        result = False
        failReason = "Account does not have a IAM password policy."
    else:
        if passwordpolicy['RequireLowercaseCharacters'] is False:
            result = False
            failReason = "Password policy does not require at least one uppercase letter"
    print({'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control})

    return {'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control}


# 1.7 Ensure IAM password policy requires at least one symbol (Scored)
def control_1_7_password_policy_symbol(passwordpolicy):
    """Summary
    Args:
        passwordpolicy (TYPE): Description
    Returns:
        TYPE: Description
    """
    result = True
    failReason = ""
    offenders = []
    control = "1.7"
    description = "Ensure IAM password policy requires at least one symbol"
    scored = True
    if passwordpolicy is False:
        result = False
        failReason = "Account does not have a IAM password policy."
    else:
        if passwordpolicy['RequireSymbols'] is False:
            result = False
            failReason = "Password policy does not require at least one symbol"
    print({'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control})

    return {'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control}


# 1.8 Ensure IAM password policy requires at least one number (Scored)
def control_1_8_password_policy_number(passwordpolicy):
    """Summary
    Args:
        passwordpolicy (TYPE): Description
    Returns:
        TYPE: Description
    """
    result = True
    failReason = ""
    offenders = []
    control = "1.8"
    description = "Ensure IAM password policy requires at least one number"
    scored = True
    if passwordpolicy is False:
        result = False
        failReason = "Account does not have a IAM password policy."
    else:
        if passwordpolicy['RequireNumbers'] is False:
            result = False
            failReason = "Password policy does not require at least one number"
    print({'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control})

    return {'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control}


# 1.9 Ensure IAM password policy requires minimum length of 14 or greater (Scored)
def control_1_9_password_policy_length(passwordpolicy):
    """Summary
    Args:
        passwordpolicy (TYPE): Description
    Returns:
        TYPE: Description
    """
    result = True
    failReason = ""
    offenders = []
    control = "1.9"
    description = "Ensure IAM password policy requires minimum length of 14 or greater"
    scored = True
    if passwordpolicy is False:
        result = False
        failReason = "Account does not have a IAM password policy."
    else:
        if passwordpolicy['MinimumPasswordLength'] < 14:
            result = False
            failReason = "Password policy does not require at least 14 characters"
    print({'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control})
    return {'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control}


# 1.10 Ensure IAM password policy prevents password reuse (Scored)
def control_1_10_password_policy_reuse(passwordpolicy):
    """Summary
    Args:
        passwordpolicy (TYPE): Description
    Returns:
        TYPE: Description
    """
    result = True
    failReason = ""
    offenders = []
    control = "1.10"
    description = "Ensure IAM password policy prevents password reuse"
    scored = True
    if passwordpolicy is False:
        result = False
        failReason = "Account does not have a IAM password policy."
    else:
        try:
            if passwordpolicy['PasswordReusePrevention'] == 24:
                pass
            else:
                result = False
                failReason = "Password policy does not prevent reusing last 24 passwords"
        except:
            result = False
            failReason = "Password policy does not prevent reusing last 24 passwords"
    print({'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control})
    return {'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control}


# 1.11 Ensure IAM password policy expires passwords within 90 days or less (Scored)
def control_1_11_password_policy_expire(passwordpolicy):
    """Summary
    Args:
        passwordpolicy (TYPE): Description
    Returns:
        TYPE: Description
    """
    result = True
    failReason = ""
    offenders = []
    control = "1.11"
    description = "Ensure IAM password policy expires passwords within 90 days or less"
    scored = True
    if passwordpolicy is False:
        result = False
        failReason = "Account does not have a IAM password policy."
    else:
        if passwordpolicy['ExpirePasswords'] is True:
            if 0 < passwordpolicy['MaxPasswordAge'] > 90:
                result = False
                failReason = "Password policy does not expire passwords after 90 days or less"
        else:
            result = False
            failReason = "Password policy does not expire passwords after 90 days or less"
    print({'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control})
    return {'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control}


# 1.12 Ensure no root account access key exists (Scored)
def control_1_12_root_key_exists(credreport):
    """Summary
    Args:
        credreport (TYPE): Description
    Returns:
        TYPE: Description
    """
    result = True
    failReason = ""
    offenders = []
    control = "1.12"
    description = "Ensure no root account access key exists"
    scored = True
    if (credreport[0]['access_key_1_active'] == "true") or (credreport[0]['access_key_2_active'] == "true"):
        result = False
        failReason = "Root have active access keys"
    print({'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control})

    return {'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control}


# 1.13 Ensure MFA is enabled for the "root" account (Scored)
def control_1_13_root_mfa_enabled():
    """Summary
    Returns:
        TYPE: Description
    """
    result = True
    failReason = ""
    offenders = []
    control = "1.13"
    description = "Ensure MFA is enabled for the root account"
    scored = True
    response = IAM_CLIENT.get_account_summary()
    if response['SummaryMap']['AccountMFAEnabled'] != 1:
        result = False
        failReason = "Root account not using MFA"
    print({'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control})
    return {'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control}


# 1.14 Ensure hardware MFA is enabled for the "root" account (Scored)
def control_1_14_root_hardware_mfa_enabled():
    """Summary
    Returns:
        TYPE: Description
    """
    result = True
    failReason = ""
    offenders = []
    control = "1.14"
    description = "Ensure hardware MFA is enabled for the root account"
    scored = True
    # First verify that root is using MFA (avoiding false positive)
    response = IAM_CLIENT.get_account_summary()
    if response['SummaryMap']['AccountMFAEnabled'] == 1:
        paginator = IAM_CLIENT.get_paginator('list_virtual_mfa_devices')
        response_iterator = paginator.paginate(
            AssignmentStatus='Any',
        )
        pagedResult = []
        for page in response_iterator:
            for n in page['VirtualMFADevices']:
                pagedResult.append(n)
        if "mfa/root-account-mfa-device" in str(pagedResult):
            failReason = "Root account not using hardware MFA"
            result = False
    else:
        result = False
        failReason = "Root account not using MFA"
    print({'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control})
    return {'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control}


# 1.15 Ensure security questions are registered in the AWS account (Not Scored/Manual)
def control_1_15_security_questions_registered():
    """Summary
    Returns:
        TYPE: Description
    """
    result = "Manual"
    failReason = ""
    offenders = []
    control = "1.15"
    description = "Ensure security questions are registered in the AWS account, please verify manually"
    scored = False
    failReason = "Control not implemented using API, please verify manually"
    print({'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control})
    return {'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control}


# 1.16 Ensure IAM policies are attached only to groups or roles (Scored)
def control_1_16_no_policies_on_iam_users():
    """Summary
    Returns:
        TYPE: Description
    """
    result = True
    failReason = ""
    offenders = []
    control = "1.16"
    description = "Ensure IAM policies are attached only to groups or roles"
    scored = True
    paginator = IAM_CLIENT.get_paginator('list_users')
    response_iterator = paginator.paginate()
    pagedResult = []
    for page in response_iterator:
        for n in page['Users']:
            pagedResult.append(n)
    offenders = []
    for n in pagedResult:
        policies = IAM_CLIENT.list_user_policies(
            UserName=n['UserName'],
            MaxItems=1
        )
        if policies['PolicyNames'] != []:
            result = False
            failReason = "IAM user have inline policy attached"
            offenders.append(str(n['Arn']))
    print({'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control})
    return {'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control}


# 1.17 Enable detailed billing (Scored)
def control_1_17_detailed_billing_enabled():
    """Summary
    Returns:
        TYPE: Description
    """
    result = "Manual"
    failReason = ""
    offenders = []
    control = "1.17"
    description = "Enable detailed billing, please verify manually"
    scored = True
    failReason = "Control not implemented using API, please verify manually"
    print({'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control})
    return {'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control}


# 1.18 Ensure IAM Master and IAM Manager roles are active (Scored)
def control_1_18_ensure_iam_master_and_manager_roles():
    """Summary
    Returns:
        TYPE: Description
    """
    result = "True"
    failReason = "No IAM Master or IAM Manager role created"
    offenders = []
    control = "1.18"
    description = "Ensure IAM Master and IAM Manager roles are active. Control under review/investigation"
    scored = True
    print({'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control})
    return {'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control}


# 1.19 Maintain current contact details (Scored)
def control_1_19_maintain_current_contact_details():
    """Summary
    Returns:
        TYPE: Description
    """
    result = "Manual"
    failReason = ""
    offenders = []
    control = "1.19"
    description = "Maintain current contact details, please verify manually"
    scored = True
    failReason = "Control not implemented using API, please verify manually"
    print({'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control})
    return {'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control}


# 1.20 Ensure security contact information is registered (Scored)
def control_1_20_ensure_security_contact_details():
    """Summary
    Returns:
        TYPE: Description
    """
    result = "Manual"
    failReason = ""
    offenders = []
    control = "1.20"
    description = "Ensure security contact information is registered, please verify manually"
    scored = True
    failReason = "Control not implemented using API, please verify manually"
    return {'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control}


# 1.21 Ensure IAM instance roles are used for AWS resource access from instances (Scored)
def control_1_21_ensure_iam_instance_roles_used():
    """Summary
    Returns:
        TYPE: Description
    """
    result = True
    failReason = ""
    offenders = []
    control = "1.21"
    description = "Ensure IAM instance roles are used for AWS resource access from instances, application code is not audited"
    scored = True
    failReason = "Instance not assigned IAM role for EC2"
    client = boto3.client('ec2')
    response = client.describe_instances()
    offenders = []
    for n, _ in enumerate(response['Reservations']):
        try:
            if response['Reservations'][n]['Instances'][0]['IamInstanceProfile']:
                pass
        except:
                result = False
                offenders.append(str(response['Reservations'][n]['Instances'][0]['InstanceId']))
    print({'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control})
    return {'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control}


# 1.22 Ensure a support role has been created to manage incidents with AWS Support (Scored)
def control_1_22_ensure_incident_management_roles():
    """Summary
    Returns:
        TYPE: Description
    """
    result = True
    failReason = ""
    offenders = []
    control = "1.22"
    description = "Ensure a support role has been created to manage incidents with AWS Support"
    scored = True
    offenders = []
    try:
        response = IAM_CLIENT.list_entities_for_policy(
            PolicyArn='arn:aws:iam::aws:policy/AWSSupportAccess'
        )
        if (len(response['PolicyGroups']) + len(response['PolicyUsers']) + len(response['PolicyRoles'])) == 0:
            result = False
            failReason = "No user, group or role assigned AWSSupportAccess"
    except:
        result = False
        failReason = "AWSSupportAccess policy not created"
    print({'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control})
    return {'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control}


# 1.23 Do not setup access keys during initial user setup for all IAM users that have a console password (Not Scored)
def control_1_23_no_active_initial_access_keys_with_iam_user(credreport):
    """Summary
    Returns:
        TYPE: Description
    """
    result = True
    failReason = ""
    offenders = []
    control = "1.23"
    description = "Do not setup access keys during initial user setup for all IAM users that have a console password"
    scored = False
    offenders = []
    for n, _ in enumerate(credreport):
        if (credreport[n]['access_key_1_active'] or credreport[n]['access_key_2_active'] == 'true') and n > 0:
            response = IAM_CLIENT.list_access_keys(
                UserName=str(credreport[n]['user'])
            )
            for m in response['AccessKeyMetadata']:
                if re.sub(r"\s", "T", str(m['CreateDate'])) == credreport[n]['user_creation_time']:
                    result = False
                    failReason = "Users with keys created at user creation time found"
                    offenders.append(str(credreport[n]['arn']) + ":" + str(m['AccessKeyId']))
    print({'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control})                  
    return {'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control}


# 1.24  Ensure IAM policies that allow full "*:*" administrative privileges are not created (Scored)
def control_1_24_no_overly_permissive_policies():
    """Summary
    Returns:
        TYPE: Description
    """
    result = True
    failReason = ""
    offenders = []
    control = "1.24"
    description = "Ensure IAM policies that allow full administrative privileges are not created"
    scored = True
    offenders = []
    paginator = IAM_CLIENT.get_paginator('list_policies')
    response_iterator = paginator.paginate(
        Scope='Local',
        OnlyAttached=False,
    )
    pagedResult = []
    for page in response_iterator:
        for n in page['Policies']:
            pagedResult.append(n)
    for m in pagedResult:
        policy = IAM_CLIENT.get_policy_version(
            PolicyArn=m['Arn'],
            VersionId=m['DefaultVersionId']
        )

        statements = []
        # a policy may contain a single statement, a single statement in an array, or multiple statements in an array
        if isinstance(policy['PolicyVersion']['Document']['Statement'], list):
            for statement in policy['PolicyVersion']['Document']['Statement']:
                statements.append(statement)
        else:
            statements.append(policy['PolicyVersion']['Document']['Statement'])

        for n in statements:
            # a policy statement has to contain either an Action or a NotAction
            if 'Action' in n.keys() and n['Effect'] == 'Allow':
                if ("'*'" in str(n['Action']) or str(n['Action']) == "*") and ("'*'" in str(n['Resource']) or str(n['Resource']) == "*"):
                    result = False
                    failReason = "Found full administrative policy"
                    offenders.append(str(m['Arn']))
    print({'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control})
    return {'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control}

# --- 2 Logging ---

# 2.1 Ensure CloudTrail is enabled in all regions (Scored)
def control_2_1_ensure_cloud_trail_all_regions(cloudtrails):
    """Summary
    Args:
        cloudtrails (TYPE): Description
    Returns:
        TYPE: Description
    """
    result = False
    failReason = ""
    offenders = []
    control = "2.1"
    description = "Ensure CloudTrail is enabled in all regions"
    scored = True
    for m, n in cloudtrails.items():
        for o in n:
            if o['IsMultiRegionTrail']:
                client = boto3.client('cloudtrail', region_name=m)
                response = client.get_trail_status(
                    Name=o['TrailARN']
                )
                if response['IsLogging'] is True:
                    result = True
                    break
    if result is False:
        failReason = "No enabled multi region trails found"
    print({'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control})
    return {'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control}


# 2.2 Ensure CloudTrail log file validation is enabled (Scored)
def control_2_2_ensure_cloudtrail_validation(cloudtrails):
    """Summary
    Args:
        cloudtrails (TYPE): Description
    Returns:
        TYPE: Description
    """
    result = True
    failReason = ""
    offenders = []
    control = "2.2"
    description = "Ensure CloudTrail log file validation is enabled"
    scored = True
    for m, n in cloudtrails.items():
        for o in n:
            if o['LogFileValidationEnabled'] is False:
                result = False
                failReason = "CloudTrails without log file validation discovered"
                offenders.append(str(o['TrailARN']))
    offenders = set(offenders)
    offenders = list(offenders)
    print({'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control})
    return {'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control}


# 2.3 Ensure the S3 bucket CloudTrail logs to is not publicly accessible (Scored)
def control_2_3_ensure_cloudtrail_bucket_not_public(cloudtrails):
    """Summary
    Args:
        cloudtrails (TYPE): Description
    Returns:
        TYPE: Description
    """
    result = True
    failReason = ""
    offenders = []
    control = "2.3"
    description = "Ensure the S3 bucket CloudTrail logs to is not publicly accessible"
    scored = True
    for m, n in cloudtrails.items():
        for o in n:
            #  We only want to check cases where there is a bucket
            if "S3BucketName" in str(o):
                try:
                    response = S3_CLIENT.get_bucket_acl(Bucket=o['S3BucketName'])
                    for p in response['Grants']:
                        # print("Grantee is " + str(p['Grantee']))
                        if re.search(r'(global/AllUsers|global/AuthenticatedUsers)', str(p['Grantee'])):
                            result = False
                            offenders.append(str(o['TrailARN']) + ":PublicBucket")
                            if "Publically" not in failReason:
                                failReason = failReason + "Publically accessible CloudTrail bucket discovered."
                except Exception as e:
                    result = False
                    if "AccessDenied" in str(e):
                        offenders.append(str(o['TrailARN']) + ":AccessDenied")
                        if "Missing" not in failReason:
                            failReason = "Missing permissions to verify bucket ACL. " + failReason
                    elif "NoSuchBucket" in str(e):
                        offenders.append(str(o['TrailARN']) + ":NoBucket")
                        if "Trailbucket" not in failReason:
                            failReason = "Trailbucket doesn't exist. " + failReason
                    else:
                        offenders.append(str(o['TrailARN']) + ":CannotVerify")
                        if "Cannot" not in failReason:
                            failReason = "Cannot verify bucket ACL. " + failReason
            else:
                result = False
                offenders.append(str(o['TrailARN']) + "NoS3Logging")
                failReason = "Cloudtrail not configured to log to S3. " + failReason
    print({'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control})
    return {'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control}


# 2.4 Ensure CloudTrail trails are integrated with CloudWatch Logs (Scored)
def control_2_4_ensure_cloudtrail_cloudwatch_logs_integration(cloudtrails):
    """Summary
    Args:
        cloudtrails (TYPE): Description
    Returns:
        TYPE: Description
    """
    result = True
    failReason = ""
    offenders = []
    control = "2.4"
    description = "Ensure CloudTrail trails are integrated with CloudWatch Logs"
    scored = True
    for m, n in cloudtrails.items():
        for o in n:
            try:
                if "arn:aws:logs" in o['CloudWatchLogsLogGroupArn']:
                    pass
                else:
                    result = False
                    failReason = "CloudTrails without CloudWatch Logs discovered"
                    offenders.append(str(o['TrailARN']))
            except:
                result = False
                failReason = "CloudTrails without CloudWatch Logs discovered"
                offenders.append(str(o['TrailARN']))
    print({'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control})
    return {'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control}


# 2.5 Ensure AWS Config is enabled in all regions (Scored)
def control_2_5_ensure_config_all_regions(regions):
    """Summary
    Returns:
        TYPE: Description
    """
    result = True
    failReason = ""
    offenders = []
    control = "2.5"
    description = "Ensure AWS Config is enabled in all regions"
    scored = True
    globalConfigCapture = False  # Only one region needs to capture global events
    for n in regions:
        configClient = boto3.client('config', region_name=n)
        response = configClient.describe_configuration_recorder_status()
        # Get recording status
        try:
            if not response['ConfigurationRecordersStatus'][0]['recording'] is True:
                result = False
                failReason = "Config not enabled in all regions, not capturing all/global events or delivery channel errors"
                offenders.append(str(n) + ":NotRecording")
        except:
            result = False
            failReason = "Config not enabled in all regions, not capturing all/global events or delivery channel errors"
            offenders.append(str(n) + ":NotRecording")

        # Verify that each region is capturing all events
        response = configClient.describe_configuration_recorders()
        try:
            if not response['ConfigurationRecorders'][0]['recordingGroup']['allSupported'] is True:
                result = False
                failReason = "Config not enabled in all regions, not capturing all/global events or delivery channel errors"
                offenders.append(str(n) + ":NotAllEvents")
        except:
            pass  # This indicates that Config is disabled in the region and will be captured above.

        # Check if region is capturing global events. Fail is verified later since only one region needs to capture them.
        try:
            if response['ConfigurationRecorders'][0]['recordingGroup']['includeGlobalResourceTypes'] is True:
                globalConfigCapture = True
        except:
            pass

        # Verify the delivery channels
        response = configClient.describe_delivery_channel_status()
        try:
            if response['DeliveryChannelsStatus'][0]['configHistoryDeliveryInfo']['lastStatus'] != "SUCCESS":
                result = False
                failReason = "Config not enabled in all regions, not capturing all/global events or delivery channel errors"
                offenders.append(str(n) + ":S3orSNSDelivery")
        except:
            pass  # Will be captured by earlier rule
        try:
            if response['DeliveryChannelsStatus'][0]['configStreamDeliveryInfo']['lastStatus'] != "SUCCESS":
                result = False
                failReason = "Config not enabled in all regions, not capturing all/global events or delivery channel errors"
                offenders.append(str(n) + ":SNSDelivery")
        except:
            pass  # Will be captured by earlier rule

    # Verify that global events is captured by any region
    if globalConfigCapture is False:
        result = False
        failReason = "Config not enabled in all regions, not capturing all/global events or delivery channel errors"
        offenders.append("Global:NotRecording")
    print({'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control})
    return {'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control}


# 2.6 Ensure S3 bucket access logging is enabled on the CloudTrail S3 bucket (Scored)
def control_2_6_ensure_cloudtrail_bucket_logging(cloudtrails):
    """Summary
    Args:
        cloudtrails (TYPE): Description
    Returns:
        TYPE: Description
    """
    result = True
    failReason = ""
    offenders = []
    control = "2.6"
    description = "Ensure S3 bucket access logging is enabled on the CloudTrail S3 bucket"
    scored = True
    for m, n in cloudtrails.items():
        for o in n:
            # it is possible to have a cloudtrail configured with a nonexistant bucket
            try:
                response = S3_CLIENT.get_bucket_logging(Bucket=o['S3BucketName'])
            except:
                result = False
                failReason = "Cloudtrail not configured to log to S3. "
                offenders.append(str(o['TrailARN']))
            try:
                if response['LoggingEnabled']:
                    pass
            except:
                result = False
                failReason = failReason + "CloudTrail S3 bucket without logging discovered"
                offenders.append("Trail:" + str(o['TrailARN']) + " - S3Bucket:" + str(o['S3BucketName']))
    print({'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control})
    return {'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control}


# 2.7 Ensure CloudTrail logs are encrypted at rest using KMS CMKs (Scored)
def control_2_7_ensure_cloudtrail_encryption_kms(cloudtrails):
    """Summary
    Args:
        cloudtrails (TYPE): Description
    Returns:
        TYPE: Description
    """
    result = True
    failReason = ""
    offenders = []
    control = "2.7"
    description = "Ensure CloudTrail logs are encrypted at rest using KMS CMKs"
    scored = True
    for m, n in cloudtrails.items():
        for o in n:
            try:
                if o['KmsKeyId']:
                    pass
            except:
                result = False
                failReason = "CloudTrail not using KMS CMK for encryption discovered"
                offenders.append("Trail:" + str(o['TrailARN']))
    print({'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control})
    return {'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control}


# 2.8 Ensure rotation for customer created CMKs is enabled (Scored)
def control_2_8_ensure_kms_cmk_rotation(regions):
    """Summary
    Returns:
        TYPE: Description
    """
    result = True
    failReason = ""
    offenders = []
    control = "2.8"
    description = "Ensure rotation for customer created CMKs is enabled"
    scored = True
    for n in regions:
        kms_client = boto3.client('kms', region_name=n)
        paginator = kms_client.get_paginator('list_keys')
        response_iterator = paginator.paginate()
        for page in response_iterator:
            for n in page['Keys']:
                try:
                    rotationStatus = kms_client.get_key_rotation_status(KeyId=n['KeyId'])
                    if rotationStatus['KeyRotationEnabled'] is False:
                        keyDescription = kms_client.describe_key(KeyId=n['KeyId'])
                        if "Default master key that protects my" not in str(keyDescription['KeyMetadata']['Description']):  # Ignore service keys
                            result = False
                            failReason = "KMS CMK rotation not enabled"
                            offenders.append("Key:" + str(keyDescription['KeyMetadata']['Arn']))
                except:
                    pass  # Ignore keys without permission, for example ACM key
    print({'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control})
    return {'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control}


# --- Monitoring ---

# 3.1 Ensure a log metric filter and alarm exist for unauthorized API calls (Scored)
def control_3_1_ensure_log_metric_filter_unauthorized_api_calls(cloudtrails):
    """Summary
    Returns:
        TYPE: Description
    """
    result = False
    failReason = ""
    offenders = []
    control = "3.1"
    description = "Ensure log metric filter unauthorized api calls"
    scored = True
    failReason = "Incorrect log metric alerts for unauthorized_api_calls"
    for m, n in cloudtrails.items():
        for o in n:
            try:
                if o['CloudWatchLogsLogGroupArn']:
                    group = re.search('log-group:(.+?):', o['CloudWatchLogsLogGroupArn']).group(1)
                    client = boto3.client('logs', region_name=m)
                    filters = client.describe_metric_filters(
                        logGroupName=group
                    )
                    for p in filters['metricFilters']:
                        patterns = ["\$\.errorCode\s*=\s*\"?\*UnauthorizedOperation(\"|\)|\s)", "\$\.errorCode\s*=\s*\"?AccessDenied\*(\"|\)|\s)"]
                        if find_in_string(patterns, str(p['filterPattern'])):
                            cwclient = boto3.client('cloudwatch', region_name=m)
                            response = cwclient.describe_alarms_for_metric(
                                MetricName=p['metricTransformations'][0]['metricName'],
                                Namespace=p['metricTransformations'][0]['metricNamespace']
                            )
                            snsClient = boto3.client('sns', region_name=m)
                            subscribers = snsClient.list_subscriptions_by_topic(
                                TopicArn=response['MetricAlarms'][0]['AlarmActions'][0]
                                #  Pagination not used since only 1 subscriber required
                            )
                            if not len(subscribers['Subscriptions']) == 0:
                                result = True
            except:
                pass
    print({'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control})
    return {'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control}


# 3.2 Ensure a log metric filter and alarm exist for Management Console sign-in without MFA (Scored)
def control_3_2_ensure_log_metric_filter_console_signin_no_mfa(cloudtrails):
    """Summary
    Returns:
        TYPE: Description
    """
    result = False
    failReason = ""
    offenders = []
    control = "3.2"
    description = "Ensure a log metric filter and alarm exist for Management Console sign-in without MFA"
    scored = True
    failReason = "Incorrect log metric alerts for management console signin without MFA"
    for m, n in cloudtrails.items():
        for o in n:
            try:
                if o['CloudWatchLogsLogGroupArn']:
                    group = re.search('log-group:(.+?):', o['CloudWatchLogsLogGroupArn']).group(1)
                    client = boto3.client('logs', region_name=m)
                    filters = client.describe_metric_filters(
                        logGroupName=group
                    )
                    for p in filters['metricFilters']:
                        patterns = ["\$\.eventName\s*=\s*\"?ConsoleLogin(\"|\)|\s)", "\$\.additionalEventData\.MFAUsed\s*\!=\s*\"?Yes"]
                        if find_in_string(patterns, str(p['filterPattern'])):
                            cwclient = boto3.client('cloudwatch', region_name=m)
                            response = cwclient.describe_alarms_for_metric(
                                MetricName=p['metricTransformations'][0]['metricName'],
                                Namespace=p['metricTransformations'][0]['metricNamespace']
                            )
                            snsClient = boto3.client('sns', region_name=m)
                            subscribers = snsClient.list_subscriptions_by_topic(
                                TopicArn=response['MetricAlarms'][0]['AlarmActions'][0]
                                #  Pagination not used since only 1 subscriber required
                            )
                            if not len(subscribers['Subscriptions']) == 0:
                                result = True
            except:
                pass
    print({'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control})
    return {'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control}


# 3.3 Ensure a log metric filter and alarm exist for usage of "root" account (Scored)
def control_3_3_ensure_log_metric_filter_root_usage(cloudtrails):
    """Summary
    Returns:
        TYPE: Description
    """
    result = False
    failReason = ""
    offenders = []
    control = "3.3"
    description = "Ensure a log metric filter and alarm exist for root usage"
    scored = True
    failReason = "Incorrect log metric alerts for root usage"
    for m, n in cloudtrails.items():
        for o in n:
            try:
                if o['CloudWatchLogsLogGroupArn']:
                    group = re.search('log-group:(.+?):', o['CloudWatchLogsLogGroupArn']).group(1)
                    client = boto3.client('logs', region_name=m)
                    filters = client.describe_metric_filters(
                        logGroupName=group
                    )
                    for p in filters['metricFilters']:
                        patterns = ["\$\.userIdentity\.type\s*=\s*\"?Root", "\$\.userIdentity\.invokedBy\s*NOT\s*EXISTS", "\$\.eventType\s*\!=\s*\"?AwsServiceEvent(\"|\)|\s)"]
                        if find_in_string(patterns, str(p['filterPattern'])):
                            cwclient = boto3.client('cloudwatch', region_name=m)
                            response = cwclient.describe_alarms_for_metric(
                                MetricName=p['metricTransformations'][0]['metricName'],
                                Namespace=p['metricTransformations'][0]['metricNamespace']
                            )
                            snsClient = boto3.client('sns', region_name=m)
                            subscribers = snsClient.list_subscriptions_by_topic(
                                TopicArn=response['MetricAlarms'][0]['AlarmActions'][0]
                                #  Pagination not used since only 1 subscriber required
                            )
                            if not len(subscribers['Subscriptions']) == 0:
                                result = True
            except:
                pass
    print({'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control})
    return {'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control}


# 3.4 Ensure a log metric filter and alarm exist for IAM policy changes  (Scored)
def control_3_4_ensure_log_metric_iam_policy_change(cloudtrails):
    """Summary
    Returns:
        TYPE: Description
    """
    result = False
    failReason = ""
    offenders = []
    control = "3.4"
    description = "Ensure a log metric filter and alarm exist for IAM changes"
    scored = True
    failReason = "Incorrect log metric alerts for IAM policy changes"
    for m, n in cloudtrails.items():
        for o in n:
            try:
                if o['CloudWatchLogsLogGroupArn']:
                    group = re.search('log-group:(.+?):', o['CloudWatchLogsLogGroupArn']).group(1)
                    client = boto3.client('logs', region_name=m)
                    filters = client.describe_metric_filters(
                        logGroupName=group
                    )
                    for p in filters['metricFilters']:
                        patterns = ["\$\.eventName\s*=\s*\"?DeleteGroupPolicy(\"|\)|\s)", "\$\.eventName\s*=\s*\"?DeleteRolePolicy(\"|\)|\s)", "\$\.eventName\s*=\s*\"?DeleteUserPolicy(\"|\)|\s)", "\$\.eventName\s*=\s*\"?PutGroupPolicy(\"|\)|\s)", "\$\.eventName\s*=\s*\"?PutRolePolicy(\"|\)|\s)", "\$\.eventName\s*=\s*\"?PutUserPolicy(\"|\)|\s)", "\$\.eventName\s*=\s*\"?CreatePolicy(\"|\)|\s)", "\$\.eventName\s*=\s*\"?DeletePolicy(\"|\)|\s)", "\$\.eventName\s*=\s*\"?CreatePolicyVersion(\"|\)|\s)", "\$\.eventName\s*=\s*\"?DeletePolicyVersion(\"|\)|\s)", "\$\.eventName\s*=\s*\"?AttachRolePolicy(\"|\)|\s)", "\$\.eventName\s*=\s*\"?DetachRolePolicy(\"|\)|\s)", "\$\.eventName\s*=\s*\"?AttachUserPolicy(\"|\)|\s)", "\$\.eventName\s*=\s*\"?DetachUserPolicy(\"|\)|\s)", "\$\.eventName\s*=\s*\"?AttachGroupPolicy(\"|\)|\s)", "\$\.eventName\s*=\s*\"?DetachGroupPolicy(\"|\)|\s)"]
                        if find_in_string(patterns, str(p['filterPattern'])):
                            cwclient = boto3.client('cloudwatch', region_name=m)
                            response = cwclient.describe_alarms_for_metric(
                                MetricName=p['metricTransformations'][0]['metricName'],
                                Namespace=p['metricTransformations'][0]['metricNamespace']
                            )
                            snsClient = boto3.client('sns', region_name=m)
                            subscribers = snsClient.list_subscriptions_by_topic(
                                TopicArn=response['MetricAlarms'][0]['AlarmActions'][0]
                                #  Pagination not used since only 1 subscriber required
                            )
                            if not len(subscribers['Subscriptions']) == 0:
                                result = True
            except:
                pass
    print({'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control})
    return {'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control}


# 3.5 Ensure a log metric filter and alarm exist for CloudTrail configuration changes (Scored)
def control_3_5_ensure_log_metric_cloudtrail_configuration_changes(cloudtrails):
    """Summary
    Returns:
        TYPE: Description
    """
    result = False
    failReason = ""
    offenders = []
    control = "3.5"
    description = "Ensure a log metric filter and alarm exist for CloudTrail configuration changes"
    scored = True
    failReason = "Incorrect log metric alerts for CloudTrail configuration changes"
    for m, n in cloudtrails.items():
        for o in n:
            try:
                if o['CloudWatchLogsLogGroupArn']:
                    group = re.search('log-group:(.+?):', o['CloudWatchLogsLogGroupArn']).group(1)
                    client = boto3.client('logs', region_name=m)
                    filters = client.describe_metric_filters(
                        logGroupName=group
                    )
                    for p in filters['metricFilters']:
                        patterns = ["\$\.eventName\s*=\s*\"?CreateTrail(\"|\)|\s)", "\$\.eventName\s*=\s*\"?UpdateTrail(\"|\)|\s)", "\$\.eventName\s*=\s*\"?DeleteTrail(\"|\)|\s)", "\$\.eventName\s*=\s*\"?StartLogging(\"|\)|\s)", "\$\.eventName\s*=\s*\"?StopLogging(\"|\)|\s)"]
                        if find_in_string(patterns, str(p['filterPattern'])):
                            cwclient = boto3.client('cloudwatch', region_name=m)
                            response = cwclient.describe_alarms_for_metric(
                                MetricName=p['metricTransformations'][0]['metricName'],
                                Namespace=p['metricTransformations'][0]['metricNamespace']
                            )
                            snsClient = boto3.client('sns', region_name=m)
                            subscribers = snsClient.list_subscriptions_by_topic(
                                TopicArn=response['MetricAlarms'][0]['AlarmActions'][0]
                                #  Pagination not used since only 1 subscriber required
                            )
                            if not len(subscribers['Subscriptions']) == 0:
                                result = True
            except:
                pass
    print({'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control})
    return {'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control}


# 3.6 Ensure a log metric filter and alarm exist for AWS Management Console authentication failures (Scored)
def control_3_6_ensure_log_metric_console_auth_failures(cloudtrails):
    """Summary
    Returns:
        TYPE: Description
    """
    result = False
    failReason = ""
    offenders = []
    control = "3.6"
    description = "Ensure a log metric filter and alarm exist for console auth failures"
    scored = True
    failReason = "Ensure a log metric filter and alarm exist for console auth failures"
    for m, n in cloudtrails.items():
        for o in n:
            try:
                if o['CloudWatchLogsLogGroupArn']:
                    group = re.search('log-group:(.+?):', o['CloudWatchLogsLogGroupArn']).group(1)
                    client = boto3.client('logs', region_name=m)
                    filters = client.describe_metric_filters(
                        logGroupName=group
                    )
                    for p in filters['metricFilters']:
                        patterns = ["\$\.eventName\s*=\s*\"?ConsoleLogin(\"|\)|\s)", "\$\.errorMessage\s*=\s*\"?Failed authentication(\"|\)|\s)"]
                        if find_in_string(patterns, str(p['filterPattern'])):
                            cwclient = boto3.client('cloudwatch', region_name=m)
                            response = cwclient.describe_alarms_for_metric(
                                MetricName=p['metricTransformations'][0]['metricName'],
                                Namespace=p['metricTransformations'][0]['metricNamespace']
                            )
                            snsClient = boto3.client('sns', region_name=m)
                            subscribers = snsClient.list_subscriptions_by_topic(
                                TopicArn=response['MetricAlarms'][0]['AlarmActions'][0]
                                #  Pagination not used since only 1 subscriber required
                            )
                            if not len(subscribers['Subscriptions']) == 0:
                                result = True
            except:
                pass
    print({'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control})
    return {'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control}


# 3.7 Ensure a log metric filter and alarm exist for disabling or scheduled deletion of customer created CMKs (Scored)
def control_3_7_ensure_log_metric_disabling_scheduled_delete_of_kms_cmk(cloudtrails):
    """Summary
    Returns:
        TYPE: Description
    """
    result = False
    failReason = ""
    offenders = []
    control = "3.7"
    description = "Ensure a log metric filter and alarm exist for disabling or scheduling deletion of KMS CMK"
    scored = True
    failReason = "Ensure a log metric filter and alarm exist for disabling or scheduling deletion of KMS CMK"
    for m, n in cloudtrails.items():
        for o in n:
            try:
                if o['CloudWatchLogsLogGroupArn']:
                    group = re.search('log-group:(.+?):', o['CloudWatchLogsLogGroupArn']).group(1)
                    client = boto3.client('logs', region_name=m)
                    filters = client.describe_metric_filters(
                        logGroupName=group
                    )
                    for p in filters['metricFilters']:
                        patterns = ["\$\.eventSource\s*=\s*\"?kms\.amazonaws\.com(\"|\)|\s)", "\$\.eventName\s*=\s*\"?DisableKey(\"|\)|\s)", "\$\.eventName\s*=\s*\"?ScheduleKeyDeletion(\"|\)|\s)"]
                        if find_in_string(patterns, str(p['filterPattern'])):
                            cwclient = boto3.client('cloudwatch', region_name=m)
                            response = cwclient.describe_alarms_for_metric(
                                MetricName=p['metricTransformations'][0]['metricName'],
                                Namespace=p['metricTransformations'][0]['metricNamespace']
                            )
                            snsClient = boto3.client('sns', region_name=m)
                            subscribers = snsClient.list_subscriptions_by_topic(
                                TopicArn=response['MetricAlarms'][0]['AlarmActions'][0]
                                #  Pagination not used since only 1 subscriber required
                            )
                            if not len(subscribers['Subscriptions']) == 0:
                                result = True
            except:
                pass
    print({'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control})
    return {'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control}


# 3.8 Ensure a log metric filter and alarm exist for S3 bucket policy changes (Scored)
def control_3_8_ensure_log_metric_s3_bucket_policy_changes(cloudtrails):
    """Summary
    Returns:
        TYPE: Description
    """
    result = False
    failReason = ""
    offenders = []
    control = "3.8"
    description = "Ensure a log metric filter and alarm exist for S3 bucket policy changes"
    scored = True
    failReason = "Ensure a log metric filter and alarm exist for S3 bucket policy changes"
    for m, n in cloudtrails.items():
        for o in n:
            try:
                if o['CloudWatchLogsLogGroupArn']:
                    group = re.search('log-group:(.+?):', o['CloudWatchLogsLogGroupArn']).group(1)
                    client = boto3.client('logs', region_name=m)
                    filters = client.describe_metric_filters(
                        logGroupName=group
                    )
                    for p in filters['metricFilters']:
                        patterns = ["\$\.eventSource\s*=\s*\"?s3\.amazonaws\.com(\"|\)|\s)", "\$\.eventName\s*=\s*\"?PutBucketAcl(\"|\)|\s)", "\$\.eventName\s*=\s*\"?PutBucketPolicy(\"|\)|\s)", "\$\.eventName\s*=\s*\"?PutBucketCors(\"|\)|\s)", "\$\.eventName\s*=\s*\"?PutBucketLifecycle(\"|\)|\s)", "\$\.eventName\s*=\s*\"?PutBucketReplication(\"|\)|\s)", "\$\.eventName\s*=\s*\"?DeleteBucketPolicy(\"|\)|\s)", "\$\.eventName\s*=\s*\"?DeleteBucketCors(\"|\)|\s)", "\$\.eventName\s*=\s*\"?DeleteBucketLifecycle(\"|\)|\s)", "\$\.eventName\s*=\s*\"?DeleteBucketReplication(\"|\)|\s)"]
                        if find_in_string(patterns, str(p['filterPattern'])):
                            cwclient = boto3.client('cloudwatch', region_name=m)
                            response = cwclient.describe_alarms_for_metric(
                                MetricName=p['metricTransformations'][0]['metricName'],
                                Namespace=p['metricTransformations'][0]['metricNamespace']
                            )
                            snsClient = boto3.client('sns', region_name=m)
                            subscribers = snsClient.list_subscriptions_by_topic(
                                TopicArn=response['MetricAlarms'][0]['AlarmActions'][0]
                                #  Pagination not used since only 1 subscriber required
                            )
                            if not len(subscribers['Subscriptions']) == 0:
                                result = True
            except:
                pass
    print({'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control})
    return {'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control}


# 3.9 Ensure a log metric filter and alarm exist for AWS Config configuration changes (Scored)
def control_3_9_ensure_log_metric_config_configuration_changes(cloudtrails):
    """Summary
    Returns:
        TYPE: Description
    """
    result = False
    failReason = ""
    offenders = []
    control = "3.9"
    description = "Ensure a log metric filter and alarm exist for for AWS Config configuration changes"
    scored = True
    failReason = "Ensure a log metric filter and alarm exist for for AWS Config configuration changes"
    for m, n in cloudtrails.items():
        for o in n:
            try:
                if o['CloudWatchLogsLogGroupArn']:
                    group = re.search('log-group:(.+?):', o['CloudWatchLogsLogGroupArn']).group(1)
                    client = boto3.client('logs', region_name=m)
                    filters = client.describe_metric_filters(
                        logGroupName=group
                    )
                    for p in filters['metricFilters']:
                        patterns = ["\$\.eventSource\s*=\s*\"?config\.amazonaws\.com(\"|\)|\s)", "\$\.eventName\s*=\s*\"?StopConfigurationRecorder(\"|\)|\s)", "\$\.eventName\s*=\s*\"?DeleteDeliveryChannel(\"|\)|\s)", "\$\.eventName\s*=\s*\"?PutDeliveryChannel(\"|\)|\s)", "\$\.eventName\s*=\s*\"?PutConfigurationRecorder(\"|\)|\s)"]
                        if find_in_string(patterns, str(p['filterPattern'])):
                            cwclient = boto3.client('cloudwatch', region_name=m)
                            response = cwclient.describe_alarms_for_metric(
                                MetricName=p['metricTransformations'][0]['metricName'],
                                Namespace=p['metricTransformations'][0]['metricNamespace']
                            )
                            snsClient = boto3.client('sns', region_name=m)
                            subscribers = snsClient.list_subscriptions_by_topic(
                                TopicArn=response['MetricAlarms'][0]['AlarmActions'][0]
                                #  Pagination not used since only 1 subscriber required
                            )
                            if not len(subscribers['Subscriptions']) == 0:
                                result = True
            except:
                pass
    print({'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control})
    return {'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control}


# 3.10 Ensure a log metric filter and alarm exist for security group changes (Scored)
def control_3_10_ensure_log_metric_security_group_changes(cloudtrails):
    """Summary
    Returns:
        TYPE: Description
    """
    result = False
    failReason = ""
    offenders = []
    control = "3.10"
    description = "Ensure a log metric filter and alarm exist for security group changes"
    scored = True
    failReason = "Ensure a log metric filter and alarm exist for security group changes"
    for m, n in cloudtrails.items():
        for o in n:
            try:
                if o['CloudWatchLogsLogGroupArn']:
                    group = re.search('log-group:(.+?):', o['CloudWatchLogsLogGroupArn']).group(1)
                    client = boto3.client('logs', region_name=m)
                    filters = client.describe_metric_filters(
                        logGroupName=group
                    )
                    for p in filters['metricFilters']:
                        patterns = ["\$\.eventName\s*=\s*\"?AuthorizeSecurityGroupIngress(\"|\)|\s)", "\$\.eventName\s*=\s*\"?AuthorizeSecurityGroupEgress(\"|\)|\s)", "\$\.eventName\s*=\s*\"?RevokeSecurityGroupIngress(\"|\)|\s)", "\$\.eventName\s*=\s*\"?RevokeSecurityGroupEgress(\"|\)|\s)", "\$\.eventName\s*=\s*\"?CreateSecurityGroup(\"|\)|\s)", "\$\.eventName\s*=\s*\"?DeleteSecurityGroup(\"|\)|\s)"]
                        if find_in_string(patterns, str(p['filterPattern'])):
                            cwclient = boto3.client('cloudwatch', region_name=m)
                            response = cwclient.describe_alarms_for_metric(
                                MetricName=p['metricTransformations'][0]['metricName'],
                                Namespace=p['metricTransformations'][0]['metricNamespace']
                            )
                            snsClient = boto3.client('sns', region_name=m)
                            subscribers = snsClient.list_subscriptions_by_topic(
                                TopicArn=response['MetricAlarms'][0]['AlarmActions'][0]
                                #  Pagination not used since only 1 subscriber required
                            )
                            if not len(subscribers['Subscriptions']) == 0:
                                result = True
            except:
                pass
    print({'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control})
    return {'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control}


# 3.11 Ensure a log metric filter and alarm exist for changes to Network Access Control Lists (NACL) (Scored)
def control_3_11_ensure_log_metric_nacl(cloudtrails):
    """Summary
    Returns:
        TYPE: Description
    """
    result = False
    failReason = ""
    offenders = []
    control = "3.11"
    description = "Ensure a log metric filter and alarm exist for changes to Network Access Control Lists (NACL)"
    scored = True
    failReason = "Ensure a log metric filter and alarm exist for changes to Network Access Control Lists (NACL)"
    for m, n in cloudtrails.items():
        for o in n:
            try:
                if o['CloudWatchLogsLogGroupArn']:
                    group = re.search('log-group:(.+?):', o['CloudWatchLogsLogGroupArn']).group(1)
                    client = boto3.client('logs', region_name=m)
                    filters = client.describe_metric_filters(
                        logGroupName=group
                    )
                    for p in filters['metricFilters']:
                        patterns = ["\$\.eventName\s*=\s*\"?CreateNetworkAcl(\"|\)|\s)", "\$\.eventName\s*=\s*\"?CreateNetworkAclEntry(\"|\)|\s)", "\$\.eventName\s*=\s*\"?DeleteNetworkAcl(\"|\)|\s)", "\$\.eventName\s*=\s*\"?DeleteNetworkAclEntry(\"|\)|\s)", "\$\.eventName\s*=\s*\"?ReplaceNetworkAclEntry(\"|\)|\s)", "\$\.eventName\s*=\s*\"?ReplaceNetworkAclAssociation(\"|\)|\s)"]
                        if find_in_string(patterns, str(p['filterPattern'])):
                            cwclient = boto3.client('cloudwatch', region_name=m)
                            response = cwclient.describe_alarms_for_metric(
                                MetricName=p['metricTransformations'][0]['metricName'],
                                Namespace=p['metricTransformations'][0]['metricNamespace']
                            )
                            snsClient = boto3.client('sns', region_name=m)
                            subscribers = snsClient.list_subscriptions_by_topic(
                                TopicArn=response['MetricAlarms'][0]['AlarmActions'][0]
                                #  Pagination not used since only 1 subscriber required
                            )
                            if not len(subscribers['Subscriptions']) == 0:
                                result = True
            except:
                pass
    print({'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control})
    return {'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control}


# 3.12 Ensure a log metric filter and alarm exist for changes to network gateways (Scored)
def control_3_12_ensure_log_metric_changes_to_network_gateways(cloudtrails):
    """Summary
    Returns:
        TYPE: Description
    """
    result = False
    failReason = ""
    offenders = []
    control = "3.12"
    description = "Ensure a log metric filter and alarm exist for changes to network gateways"
    scored = True
    failReason = "Ensure a log metric filter and alarm exist for changes to network gateways"
    for m, n in cloudtrails.items():
        for o in n:
            try:
                if o['CloudWatchLogsLogGroupArn']:
                    group = re.search('log-group:(.+?):', o['CloudWatchLogsLogGroupArn']).group(1)
                    client = boto3.client('logs', region_name=m)
                    filters = client.describe_metric_filters(
                        logGroupName=group
                    )
                    for p in filters['metricFilters']:
                        patterns = ["\$\.eventName\s*=\s*\"?CreateCustomerGateway(\"|\)|\s)", "\$\.eventName\s*=\s*\"?DeleteCustomerGateway(\"|\)|\s)", "\$\.eventName\s*=\s*\"?AttachInternetGateway(\"|\)|\s)", "\$\.eventName\s*=\s*\"?CreateInternetGateway(\"|\)|\s)", "\$\.eventName\s*=\s*\"?DeleteInternetGateway(\"|\)|\s)", "\$\.eventName\s*=\s*\"?DetachInternetGateway(\"|\)|\s)"]
                        if find_in_string(patterns, str(p['filterPattern'])):
                            cwclient = boto3.client('cloudwatch', region_name=m)
                            response = cwclient.describe_alarms_for_metric(
                                MetricName=p['metricTransformations'][0]['metricName'],
                                Namespace=p['metricTransformations'][0]['metricNamespace']
                            )
                            snsClient = boto3.client('sns', region_name=m)
                            subscribers = snsClient.list_subscriptions_by_topic(
                                TopicArn=response['MetricAlarms'][0]['AlarmActions'][0]
                                #  Pagination not used since only 1 subscriber required
                            )
                            if not len(subscribers['Subscriptions']) == 0:
                                result = True
            except:
                pass
    print({'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control})
    return {'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control}


# 3.13 Ensure a log metric filter and alarm exist for route table changes (Scored)
def control_3_13_ensure_log_metric_changes_to_route_tables(cloudtrails):
    """Summary
    Returns:
        TYPE: Description
    """
    result = False
    failReason = ""
    offenders = []
    control = "3.13"
    description = "Ensure a log metric filter and alarm exist for route table changes"
    scored = True
    failReason = "Ensure a log metric filter and alarm exist for route table changes"
    for m, n in cloudtrails.items():
        for o in n:
            try:
                if o['CloudWatchLogsLogGroupArn']:
                    group = re.search('log-group:(.+?):', o['CloudWatchLogsLogGroupArn']).group(1)
                    client = boto3.client('logs', region_name=m)
                    filters = client.describe_metric_filters(
                        logGroupName=group
                    )
                    for p in filters['metricFilters']:
                        patterns = ["\$\.eventName\s*=\s*\"?CreateRoute(\"|\)|\s)", "\$\.eventName\s*=\s*\"?CreateRouteTable(\"|\)|\s)", "\$\.eventName\s*=\s*\"?ReplaceRoute(\"|\)|\s)", "\$\.eventName\s*=\s*\"?ReplaceRouteTableAssociation(\"|\)|\s)", "\$\.eventName\s*=\s*\"?DeleteRouteTable(\"|\)|\s)", "\$\.eventName\s*=\s*\"?DeleteRoute(\"|\)|\s)", "\$\.eventName\s*=\s*\"?DisassociateRouteTable(\"|\)|\s)"]
                        if find_in_string(patterns, str(p['filterPattern'])):
                            cwclient = boto3.client('cloudwatch', region_name=m)
                            response = cwclient.describe_alarms_for_metric(
                                MetricName=p['metricTransformations'][0]['metricName'],
                                Namespace=p['metricTransformations'][0]['metricNamespace']
                            )
                            snsClient = boto3.client('sns', region_name=m)
                            subscribers = snsClient.list_subscriptions_by_topic(
                                TopicArn=response['MetricAlarms'][0]['AlarmActions'][0]
                                #  Pagination not used since only 1 subscriber required
                            )
                            if not len(subscribers['Subscriptions']) == 0:
                                result = True
            except:
                pass
    print({'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control})
    return {'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control}


# 3.14 Ensure a log metric filter and alarm exist for VPC changes (Scored)
def control_3_14_ensure_log_metric_changes_to_vpc(cloudtrails):
    """Summary
    Returns:
        TYPE: Description
    """
    result = False
    failReason = ""
    offenders = []
    control = "3.14"
    description = "Ensure a log metric filter and alarm exist for VPC changes"
    scored = True
    failReason = "Ensure a log metric filter and alarm exist for VPC changes"
    for m, n in cloudtrails.items():
        for o in n:
            try:
                if o['CloudWatchLogsLogGroupArn']:
                    group = re.search('log-group:(.+?):', o['CloudWatchLogsLogGroupArn']).group(1)
                    client = boto3.client('logs', region_name=m)
                    filters = client.describe_metric_filters(
                        logGroupName=group
                    )
                    for p in filters['metricFilters']:
                        patterns = ["\$\.eventName\s*=\s*\"?CreateVpc(\"|\)|\s)", "\$\.eventName\s*=\s*\"?DeleteVpc(\"|\)|\s)", "\$\.eventName\s*=\s*\"?ModifyVpcAttribute(\"|\)|\s)", "\$\.eventName\s*=\s*\"?AcceptVpcPeeringConnection(\"|\)|\s)", "\$\.eventName\s*=\s*\"?CreateVpcPeeringConnection(\"|\)|\s)", "\$\.eventName\s*=\s*\"?DeleteVpcPeeringConnection(\"|\)|\s)", "\$\.eventName\s*=\s*\"?RejectVpcPeeringConnection(\"|\)|\s)", "\$\.eventName\s*=\s*\"?AttachClassicLinkVpc(\"|\)|\s)", "\$\.eventName\s*=\s*\"?DetachClassicLinkVpc(\"|\)|\s)", "\$\.eventName\s*=\s*\"?DisableVpcClassicLink(\"|\)|\s)", "\$\.eventName\s*=\s*\"?EnableVpcClassicLink(\"|\)|\s)"]
                        if find_in_string(patterns, str(p['filterPattern'])):
                            cwclient = boto3.client('cloudwatch', region_name=m)
                            response = cwclient.describe_alarms_for_metric(
                                MetricName=p['metricTransformations'][0]['metricName'],
                                Namespace=p['metricTransformations'][0]['metricNamespace']
                            )
                            snsClient = boto3.client('sns', region_name=m)
                            subscribers = snsClient.list_subscriptions_by_topic(
                                TopicArn=response['MetricAlarms'][0]['AlarmActions'][0]
                                #  Pagination not used since only 1 subscriber required
                            )
                            if not len(subscribers['Subscriptions']) == 0:
                                result = True
            except:
                pass
    print({'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control})
    return {'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control}


# 3.15 Ensure appropriate subscribers to each SNS topic (Not Scored)
def control_3_15_verify_sns_subscribers():
    """Summary
    Returns:
        TYPE: Description
    """
    result = "Manual"
    failReason = ""
    offenders = []
    control = "3.15"
    description = "Ensure appropriate subscribers to each SNS topic, please verify manually"
    scored = False
    failReason = "Control not implemented using API, please verify manually"
    print({'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control})
    return {'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control}




#####   Network   ######
# 4.1 Ensure no security groups allow ingress from 0.0.0.0/0 to port 22 (Scored)
def control_4_1_ensure_ssh_not_open_to_world(regions):
    """Summary
    Returns:
        TYPE: Description
    """
    result = True
    failReason = ""
    offenders = []
    control = "4.1"
    description = "Ensure no security groups allow ingress from 0.0.0.0/0 to port 22"
    scored = True
    for n in regions:
        client = boto3.client('ec2', region_name=n)
        response = client.describe_security_groups()
        for m in response['SecurityGroups']:
            if "0.0.0.0/0" in str(m['IpPermissions']):
                for o in m['IpPermissions']:
                    try:
                        if int(o['FromPort']) <= 22 <= int(o['ToPort']) and '0.0.0.0/0' in str(o['IpRanges']):
                            result = False
                            failReason = "Found Security Group with port 22 open to the world (0.0.0.0/0)"
                            offenders.append(str(m['GroupId']))
                    except:
                        if str(o['IpProtocol']) == "-1" and '0.0.0.0/0' in str(o['IpRanges']):
                            result = False
                            failReason = "Found Security Group with port 22 open to the world (0.0.0.0/0)"
                            offenders.append(str(n) + " : " + str(m['GroupId']))
    print({'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control})
    return {'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control}


# 4.2 Ensure no security groups allow ingress from 0.0.0.0/0 to port 3389 (Scored)
def control_4_2_ensure_rdp_not_open_to_world(regions):
    """Summary
    Returns:
        TYPE: Description
    """
    result = True
    failReason = ""
    offenders = []
    control = "4.2"
    description = "Ensure no security groups allow ingress from 0.0.0.0/0 to port 3389"
    scored = True
    for n in regions:
        client = boto3.client('ec2', region_name=n)
        response = client.describe_security_groups()
        for m in response['SecurityGroups']:
            if "0.0.0.0/0" in str(m['IpPermissions']):
                for o in m['IpPermissions']:
                    try:
                        if int(o['FromPort']) <= 3389 <= int(o['ToPort']) and '0.0.0.0/0' in str(o['IpRanges']):
                            result = False
                            failReason = "Found Security Group with port 3389 open to the world (0.0.0.0/0)"
                            offenders.append(str(m['GroupId']))
                    except:
                        if str(o['IpProtocol']) == "-1" and '0.0.0.0/0' in str(o['IpRanges']):
                            result = False
                            failReason = "Found Security Group with port 3389 open to the world (0.0.0.0/0)"
                            offenders.append(str(n) + " : " + str(m['GroupId']))
    print({'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control})
    return {'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control}


# 4.3 Ensure VPC flow logging is enabled in all VPCs (Scored)
def control_4_3_ensure_flow_logs_enabled_on_all_vpc(regions):
    """Summary
    Returns:
        TYPE: Description
    """
    result = True
    failReason = ""
    offenders = []
    control = "4.3"
    description = "Ensure VPC flow logging is enabled in all VPCs"
    scored = True
    for n in regions:
        client = boto3.client('ec2', region_name=n)
        flowlogs = client.describe_flow_logs(
            #  No paginator support in boto atm.
        )
        activeLogs = []
        for m in flowlogs['FlowLogs']:
            if "vpc-" in str(m['ResourceId']):
                activeLogs.append(m['ResourceId'])
        vpcs = client.describe_vpcs(
            Filters=[
                {
                    'Name': 'state',
                    'Values': [
                        'available',
                    ]
                },
            ]
        )
        for m in vpcs['Vpcs']:
            if not str(m['VpcId']) in str(activeLogs):
                result = False
                failReason = "VPC without active VPC Flow Logs found"
                offenders.append(str(n) + " : " + str(m['VpcId']))
    print({'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control})
    return {'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control}


# 4.4 Ensure the default security group of every VPC restricts all traffic (Scored)
def control_4_4_ensure_default_security_groups_restricts_traffic(regions):
    """Summary
    Returns:
        TYPE: Description
    """
    result = True
    failReason = ""
    offenders = []
    control = "4.4"
    description = "Ensure the default security group of every VPC restricts all traffic"
    scored = True
    for n in regions:
        client = boto3.client('ec2', region_name=n)
        response = client.describe_security_groups(
            Filters=[
                {
                    'Name': 'group-name',
                    'Values': [
                        'default',
                    ]
                },
            ]
        )
        for m in response['SecurityGroups']:
            if not (len(m['IpPermissions']) + len(m['IpPermissionsEgress'])) == 0:
                result = False
                failReason = "Default security groups with ingress or egress rules discovered"
                offenders.append(str(n) + " : " + str(m['GroupId']))
    print({'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control})
    return {'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control}


# 4.5 Ensure routing tables for VPC peering are "least access" (Not Scored)
def control_4_5_ensure_route_tables_are_least_access(regions):
    """Summary
    Returns:
        TYPE: Description
    """
    result = True
    failReason = ""
    offenders = []
    control = "4.5"
    description = "Ensure routing tables for VPC peering are least access"
    scored = False
    for n in regions:
        client = boto3.client('ec2', region_name=n)
        response = client.describe_route_tables()
        for m in response['RouteTables']:
            for o in m['Routes']:
                try:
                    if o['VpcPeeringConnectionId']:
                        if int(str(o['DestinationCidrBlock']).split("/", 1)[1]) < 24:
                            result = False
                            failReason = "Large CIDR block routed to peer discovered, please investigate"
                            offenders.append(str(n) + " : " + str(m['RouteTableId']))
                except:
                    pass
    print({'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control})
    return {'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control}




def get_cred_report():
    """Summary
    Returns:
        TYPE: Description
    """
    x = 0
    status = ""
    while IAM_CLIENT.generate_credential_report()['State'] != "COMPLETE":
        time.sleep(2)
        x += 1
        # If no credentail report is delivered within this time fail the check.
        if x > 10:
            status = "Fail: rootUse - no CredentialReport available."
            break
    if "Fail" in status:
        return status
    response = IAM_CLIENT.get_credential_report()
    credreport = []
    reader = csv.DictReader(response['Content'].decode('utf-8').splitlines(), delimiter=',')
    for row in reader:
        credreport.append(row)

    # Verify if root key's never been used, if so add N/A
    try:
        if credreport[0]['access_key_1_last_used_date']:
            pass
    except:
        credreport[0]['access_key_1_last_used_date'] = "N/A"
    try:
        if credreport[0]['access_key_2_last_used_date']:
            pass
    except:
        credreport[0]['access_key_2_last_used_date'] = "N/A"
    print("########################### Credential Report #######################")
    print(credreport)
    return credreport


def get_account_password_policy():
    """Check if a IAM password policy exists, if not return false
    Returns:
        Account IAM password policy or False
    """
    try:
        response = IAM_CLIENT.get_account_password_policy()
        print(response['PasswordPolicy'])
        return response['PasswordPolicy']
    except Exception as e:
        if "cannot be found" in str(e):
            return False


def get_regions():
    """Summary
    Returns:
        TYPE: Description
    """
    client = boto3.client('ec2')
    region_response = client.describe_regions()
    regions = [region['RegionName'] for region in region_response['Regions']]
    print("########################## Region #############################")
    print(regions)
    return regions


def get_cloudtrails(regions):
    """Summary
    Returns:
        TYPE: Description
    """
    trails = dict()
    for n in regions:
        client = boto3.client('cloudtrail', region_name=n)
        response = client.describe_trails()
        temp = []
        for m in response['trailList']:
            if m['IsMultiRegionTrail'] is True:
                if m['HomeRegion'] == n:
                    temp.append(m)
            else:
                temp.append(m)
        if len(temp) > 0:
            trails[n] = temp
    print(trails)
    return trails


def create_multipart_message(sender: str, recipients: list, title: str, text: str=None, html: str=None, attachments: list=None) -> MIMEMultipart:
    multipart_content_subtype = 'alternative' if text and html else 'mixed'
    msg = MIMEMultipart(multipart_content_subtype)
    msg['Subject'] = title
    msg['From'] = sender
    msg['To'] = ', '.join(recipients)
    if text:
        part = MIMEText(text, 'plain')
        msg.attach(part)
    if html:
        part = MIMEText(html, 'html')
        msg.attach(part)
    for attachment in attachments or []:
        with open(attachment, 'rb') as f:
            part = MIMEApplication(f.read())
            part.add_header('Content-Disposition', 'attachment', filename=os.path.basename(attachment))
            msg.attach(part)
    return msg

def send_mail(sender: str, recipients: list, title: str, text: str=None, html: str=None, attachments: list=None) -> dict:
    msg = create_multipart_message(sender, recipients, title, text, html, attachments)
    ses_client = boto3.client('ses')  # Use your settings here
    return ses_client.send_raw_email(
        Source=sender,
        Destinations=recipients,
        RawMessage={'Data': msg.as_string()}
    )
    

def mail_function():
    sender_ = '<pratyushrg@gmail.com>'
    #recipients_ = ['Recipient One <recipient_1@email.com>', 'recipient_2@email.com']
    recipients_ = ['pratyushrg@gmail.com','splis@gsu.edu']
    title_ = 'AWS hardening Audit Notification'
    text_ = 'The text version\nwith multiple lines.'
    body_ = """<html>
  <head></head>
  <body>
    <p>Hi Team<p>
    <p> <p>
    <p>Please refer to the above attachment for Audit details</p>
    <p> <p>
    <p>Thank you<p>
  </body>
  </html>
            """ 
    attachments_ = ['/tmp/AWS_hardening.csv']

    response_ = send_mail(sender_, recipients_, title_, text_, body_, attachments_)
    print(response_)

def Gen_csv(data):
  csvfile=open('/tmp/AWS_hardening.csv','w', newline='')
  obj=csv.writer(csvfile)
  for val in data:
    obj.writerow(val)
  csvfile.close()
  
def lambda_handler(event, context):
    region_list=get_regions()
    password_policy = get_account_password_policy()
    cred_report=get_cred_report()
    cloud_trails = get_cloudtrails(region_list)

    print("####################################1.IDENTITY ACCESS MANAGEMENT(IAM)############################")
    control1 = []

    control1.append(control_1_1_root_use(cred_report))
    control1.append(control_1_2_mfa_on_password_enabled_iam(cred_report))
    control1.append(control_1_3_unused_credentials(cred_report))
    control1.append(control_1_4_rotated_keys(cred_report))
    control1.append(control_1_5_password_policy_uppercase(password_policy))
    control1.append(control_1_6_password_policy_lowercase(password_policy))
    control1.append(control_1_7_password_policy_symbol(password_policy))
    control1.append(control_1_8_password_policy_number(password_policy))
    control1.append(control_1_9_password_policy_length(password_policy))
    control1.append(control_1_10_password_policy_reuse(password_policy))
    control1.append(control_1_11_password_policy_expire(password_policy))
    control1.append(control_1_12_root_key_exists(cred_report))
    control1.append(control_1_13_root_mfa_enabled())
    control1.append(control_1_14_root_hardware_mfa_enabled())
    control1.append(control_1_15_security_questions_registered())
    control1.append(control_1_16_no_policies_on_iam_users())
    control1.append(control_1_17_detailed_billing_enabled())
    control1.append(control_1_18_ensure_iam_master_and_manager_roles())
    control1.append(control_1_19_maintain_current_contact_details())
    control1.append(control_1_20_ensure_security_contact_details())
    control1.append(control_1_21_ensure_iam_instance_roles_used())
    control1.append(control_1_22_ensure_incident_management_roles())
    control1.append(control_1_23_no_active_initial_access_keys_with_iam_user(cred_report))
    control1.append(control_1_24_no_overly_permissive_policies())
    print("############################################2.LOGGING##############################################")
    control2 = []
    control2.append(control_2_1_ensure_cloud_trail_all_regions(cloud_trails))
    control2.append(control_2_2_ensure_cloudtrail_validation(cloud_trails))
    control2.append(control_2_3_ensure_cloudtrail_bucket_not_public(cloud_trails))
    control2.append(control_2_4_ensure_cloudtrail_cloudwatch_logs_integration(cloud_trails))
    control2.append(control_2_5_ensure_config_all_regions(region_list))
    control2.append(control_2_6_ensure_cloudtrail_bucket_logging(cloud_trails))
    control2.append(control_2_7_ensure_cloudtrail_encryption_kms(cloud_trails))
    #control2.append(control_2_8_ensure_kms_cmk_rotation(region_list))
    print("#############################################3.MONITORING###########################################")
    control3 = []
    control3.append(control_3_1_ensure_log_metric_filter_unauthorized_api_calls(cloud_trails))
    control3.append(control_3_2_ensure_log_metric_filter_console_signin_no_mfa(cloud_trails))
    control3.append(control_3_3_ensure_log_metric_filter_root_usage(cloud_trails))
    control3.append(control_3_4_ensure_log_metric_iam_policy_change(cloud_trails))
    control3.append(control_3_5_ensure_log_metric_cloudtrail_configuration_changes(cloud_trails))
    control3.append(control_3_6_ensure_log_metric_console_auth_failures(cloud_trails))
    control3.append(control_3_7_ensure_log_metric_disabling_scheduled_delete_of_kms_cmk(cloud_trails))
    control3.append(control_3_8_ensure_log_metric_s3_bucket_policy_changes(cloud_trails))
    control3.append(control_3_9_ensure_log_metric_config_configuration_changes(cloud_trails))
    control3.append(control_3_10_ensure_log_metric_security_group_changes(cloud_trails))
    control3.append(control_3_11_ensure_log_metric_nacl(cloud_trails))
    control3.append(control_3_12_ensure_log_metric_changes_to_network_gateways(cloud_trails))
    control3.append(control_3_13_ensure_log_metric_changes_to_route_tables(cloud_trails))
    control3.append(control_3_14_ensure_log_metric_changes_to_vpc(cloud_trails))
    control3.append(control_3_15_verify_sns_subscribers())
    print("*############################################4.NETWORKING###########################################")
    control4 = []
    control4.append(control_4_1_ensure_ssh_not_open_to_world(region_list))
    control4.append(control_4_2_ensure_rdp_not_open_to_world(region_list))
    control4.append(control_4_3_ensure_flow_logs_enabled_on_all_vpc(region_list))
    control4.append(control_4_4_ensure_default_security_groups_restricts_traffic(region_list))
    control4.append(control_4_5_ensure_route_tables_are_least_access(region_list))
    print("**********************************************  - END - ***********************************************")
    #{'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored, 'Description': description, 'ControlId': control}
    data=[['ControlId', 'Description','Result', 'failReason', 'Offenders']]
    
    for val in control1:
      data.append([val['ControlId'], val['Description'],val['Result'],val['failReason'], val['Offenders']])
    
    for val in control2:
      data.append([val['ControlId'], val['Description'],val['Result'],val['failReason'], val['Offenders']])
      
    for val in control3:
      data.append([val['ControlId'], val['Description'],val['Result'],val['failReason'], val['Offenders']])
      
    for val in control4:
      data.append([val['ControlId'], val['Description'],val['Result'],val['failReason'], val['Offenders']])
      
    Gen_csv(data)
    mail_function()
