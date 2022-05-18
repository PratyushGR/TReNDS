import os
import csv
import json
import boto3
import itertools 
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication


client=boto3.client('iam')

def passwordpolicy():
    passwordPolicy = client.get_account_password_policy()['PasswordPolicy']
    data=''
    data=data+'-----------------------------------------\n            PASSWORD POLICY              \n-----------------------------------------\n'
    for key, value in passwordPolicy.items():
        data=data+key+' : '+str(value)+'\n'
    return data
    
def MFA_get():
    mfaEnabled = []
    mfaNotEnabled=[]
    List_Users = client.list_users()
    for user in List_Users['Users']:
        login_profile= client.list_mfa_devices(UserName = user['UserName'])
        if login_profile['MFADevices'] == []:
            #print(user['UserName']+" has NO MFADevice")
            mfaNotEnabled.append(user['UserName'])
            
        else:
            #print(user['UserName']+" has MFADevice")
            mfaEnabled.append(user['UserName'])
    return mfaEnabled
    
def Gen_csv(data,name):
  csvfile=open('/tmp/'+name,'w', newline='')
  obj=csv.writer(csvfile)
  for val in data:
    obj.writerow(val)
  csvfile.close()

def Gen_text(data,name):
  f = open('/tmp/'+name,'w')
  f.write(data)
  f.close()




def userlist():
  users = client.list_users()
  data=[]
  for key in users['Users']:
    user_data={}
    user_data.update({'UserName':key['UserName']})
    user_data.update({'user_details':user_details(key['UserName'])})
    user_data.update({'password_details':password_details(key['UserName'])})
    user_data.update({'policy_names':policy_names(key['UserName'])})
    user_data.update({'grups':group_names(key['UserName'])})
    data.append(user_data)
  return data  
  
def policy_names(user_name):
    response = client.list_user_policies(UserName=user_name)
    data=[]
    try:
        if(len(response['PolicyNames']))>0:
            for pname in response['PolicyNames']:
                data.append(pname)
        else:
          data.append('NO POLICIES') 
    except:
        data.append('NO POLICIES')
    return {'INLINE_POCILIES':data}
                
    
def user_details(user_name):
  response = client.get_user(UserName=user_name)
  data={}
  try:
    data.update({'user_creation_date':(response['User']['CreateDate'])})
    try:
      data.update({'user_last_password_used_date':response['User']['PasswordLastUsed']})
    except:
      data.update({'user_last_password_used_date':'NO_DATA'})
  except:
    data.update({user_name:'NO_DATA'})
  return data

def password_details(user_name):
  data={}
  try:
    response = client.get_login_profile(UserName=user_name)
    data.update({'password_creation_date':response['LoginProfile']['CreateDate']})
  except:
    data.update({'password_creation_date':'NO_PASSWORD'})
  return data

def group_names(user_name):
    response = client.list_groups_for_user(UserName=user_name)
    data={'GROUPS':{}}
    if(len(response['Groups'])>0):
        for gnames in response['Groups']:
            data['GROUPS'].update({gnames['GroupName']:{}})
            data['GROUPS'][gnames['GroupName']].update({'GROUP_ID':gnames['GroupId']})
            data['GROUPS'][gnames['GroupName']].update(group_inline_policy(gnames['GroupName']))
            data['GROUPS'][gnames['GroupName']].update(group_managed_policy(gnames['GroupName']))
    else:
        data.update({'GROUPS':'NO_GROUPS'})
    return(data)

def group_inline_policy(group_name):
  response = client.list_group_policies(GroupName=group_name)
  data=[]
  try:
    if(len(response['PolicyNames']))>0:
      for pname in response['PolicyNames']:
        data.append(pname)        
      else:
        data.append('NO POLICIES')
  except:
    data.append('NO POLICIES')
  return {"GROUP_INLINE_POLICIES":data}

def group_managed_policy(group_name):
  response = client.list_attached_group_policies(GroupName=group_name)
  data=[]
  if(len(response['AttachedPolicies'])>0):
    for pname in response['AttachedPolicies']:
      data.append(pname['PolicyName'])
  else:
    data.append('NO POLICIES')
  return {"GROUP_MANAGED_POLICIES":data}
  
def format_group_data(group_data):
  data=[]
  data.append(['USER_NAME','GROUP_NAME','GROUP_ID','GROUP_INLINE_POLICIES','GROUP_MANAGED_POLICIES'])
  for val in group_data:
    try:
      if(val[1]=='NO_GROUPS'):
        data.append([val[0],val[1],'','',''])
      else:
        count=0
        for group in val[1]:
            if(count==0):
                data.append([val[0],group,val[1][group]['GROUP_ID'],val[1][group]['GROUP_INLINE_POLICIES'],val[1][group]['GROUP_MANAGED_POLICIES']])
                count=count+1
            else:
                data.append(['',group,val[1][group]['GROUP_ID'],val[1][group]['GROUP_INLINE_POLICIES'],val[1][group]['GROUP_MANAGED_POLICIES']])
    except:
      print('data missmatch error')
  return data

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
    

def mail():
    sender_ = '<pratyushrg@gmail.com>'
    #recipients_ = ['Recipient One <recipient_1@email.com>', 'recipient_2@email.com']
    recipients_ = ['pratyushrg@gmail.com','splis@gsu.edu']
    title_ = 'IAM-User-PasswordPolicy&GroupDetails'
    text_ = 'The text version\nwith multiple lines.'
    body_ = """<html>
  <head></head>
  <body>
    <p>Hi Team<p>
    <p> <p>
    <p>Please refer to the above attachment for user audit details</p>
    <p> <p>
    <p>Thank you<p>
  </body>
  </html>
            """ 
    attachments_ = ['/tmp/User_Password_policies_details.txt','/tmp/User_policy_details.csv','/tmp/User_group_details.csv','/tmp/User_password_details.csv']

    response_ = send_mail(sender_, recipients_, title_, text_, body_, attachments_)
    print(response_)

def main():
  user_data=userlist()
  data=[]
  data.append(['USER NAME','MFA USER','USER CREATION DATE','USER PASSWORD CREATION DATE','USER LAST PASSWORD USED DATE'])
  policy_data=[]
  policy_data.append(['USER NAME','INLINE_POCILIES'])
  group_data=[]
  mfa_users=MFA_get()
  for val in user_data:
    temp=[]
    temp1=[]
    temp2=[]
    temp.append(val['UserName'])
    temp1.append(val['UserName'])
    temp2.append(val['UserName'])
    if(val['UserName'] in mfa_users):
      temp.append('MFA USER')
    else:
      temp.append('NOT AN MFA USER')
    try:
      temp.append(val['user_details']['user_creation_date'].strftime('%d-%m-%Y'))
    except:
      temp.append('NO_USER_CREATION_DATE')
    try:
      temp.append(val['password_details']['password_creation_date'].strftime('%d-%m-%Y'))
    except:
      temp.append('NO_PASSWORD_CREATION_DATE')
    try:
      temp.append(val['user_details']['user_last_password_used_date'].strftime('%d-%m-%Y'))
    except:
      temp.append('NO_PASSWORD_LAST_USED_DATE')
      
    temp1.append(val['policy_names']['INLINE_POCILIES'])
    temp2.append(val['grups']['GROUPS'])
    data.append(temp)
    policy_data.append(temp1)
    group_data.append(temp2)
    
  Gen_text(passwordpolicy(),'User_Password_policies_details.txt')
  Gen_csv(data,'User_password_details.csv')
  Gen_csv(policy_data,'User_policy_details.csv')
  Gen_csv(format_group_data(group_data),'User_group_details.csv')
  mail()
  
def lambda_handler(event, context):
  main()
