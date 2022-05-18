import os
import csv
import json
import time
import boto3
import itertools 
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

#boto3 call to use iam related info
client=boto3.client('iam')


#function whic converts generartes multipart message witnh sender, receiver, attachements,body etc as compatible for ses service  
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

#function which sends mail using SES service
def send_mail(sender: str, recipients: list, title: str, text: str=None, html: str=None, attachments: list=None) -> dict:
    msg = create_multipart_message(sender, recipients, title, text, html, attachments)#function call to generate multipart message
    ses_client = boto3.client('ses')  # Use your settings here
    return ses_client.send_raw_email(
        Source=sender,
        Destinations=recipients,
        RawMessage={'Data': msg.as_string()}
    )
    

#function to assingne all requirements for sending mail through SES
def mail_function(name):
    sender_ = '<pratyushrg@gmail.com>'#sender email id 
    recipients_ = ['pratyushrg@gmail.com']#recepients list which are while listed in ses emails
    title_ = 'AA-Pam SOC-IAM-Notification'#subject of mail
    text_ = 'The text version\nwith multiple lines.'
    #body of mail
    body_ = """<html>
  <head></head>
  <body>
    <p>Hi Team<p>
    <p> <p>
    <p>Please refer to the above attachment for IAM user details</p>
    <p> <p>
    <p>Thank you<p>
  </body>
  </html>
            """ 
    attachments_ = ['/tmp/'+name]#attachment files paths

    response_ = send_mail(sender_, recipients_, title_, text_, body_, attachments_)#function call to send mail with above mentioned info

#function which gets all mfa enabed users list
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
    


#function to generate a csv in tmp folder with five name, data
def Gen_csv(data,name):
  csvfile=open('/tmp/'+name,'w', newline='')
  obj=csv.writer(csvfile)
  for val in data:
    obj.writerow(val)
  csvfile.close()

#function for getting user data(usename,user cration date, password data etc)
def userlist():
  users = client.list_users()
  data=[]
  for key in users['Users']:
    user_data={}
    user_data.update({'UserName':key['UserName']})
    user_data.update({'user_details':user_details(key['UserName'])})#function call for getting user related info
    user_data.update({'password_details':password_details(key['UserName'])})#function call to get password ceation date of user
    data.append(user_data)
  return data  

# function call to get all related info of a user
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

#function to get password cration date for a user
def password_details(user_name):
  data={}
  try:
    response = client.get_login_profile(UserName=user_name)
    data.update({'password_creation_date':response['LoginProfile']['CreateDate']})
  except:
    data.update({'password_creation_date':'NO_PASSWORD'})
  return data
  

#main functio which call all the above functions as per the requirement to send the alert mails
def main():
  user_data=userlist()
  data=[]
  data.append(['USER NAME','MFA USER','USER CREATION DATE','USER PASSWORD LAST UPDATED DATE','USER LAST PASSWORD USED DATE','IS USER VALIDATED'])
  mfa_users=MFA_get()
  validate=0
  date_N_days_ago = (datetime.now() - timedelta(days=90)).strftime('%d-%m-%Y')
  print(date_N_days_ago)
  non_mfa_users=[['NON MFA USERS']]
  users_password_creation_age_90=[['USERS WITH PASSWORD AGE MORE THAN 90 DAYS']]
  users_password_used_age_90=[['USERS WITH PASSWORD LAST USED DATE MORE THAN 90 DAYS']]
  for val in user_data:
    temp=[]
    count=0
    temp.append(val['UserName'])
    if(val['UserName'] in mfa_users):
      temp.append(['MFA USER'])
    else:
      temp.append('NOT AN MFA USER')
      if(len(val['UserName'].split('@'))>1):
        non_mfa_users.append([val['UserName']])
      count=count+1
    try:
      temp.append(val['user_details']['user_creation_date'].strftime('%d-%m-%Y'))
    except:
      temp.append('NO_USER_CREATION_DATE')
    try:
      temp.append(val['password_details']['password_creation_date'].strftime('%d-%m-%Y'))
    except:
      temp.append('NO_PASSWORD_CREATION_DATE')
      count=count+1
    try:
      temp.append(val['user_details']['user_last_password_used_date'].strftime('%d-%m-%Y'))
    except:
      temp.append('NO_PASSWORD_LAST_USED_DATE')
      count=count+1
    
    if(temp[4]!='NO_PASSWORD_LAST_USED_DATE'):
      if(time.strptime(temp[4],"%d-%m-%Y")<time.strptime(date_N_days_ago,"%d-%m-%Y")):
        if(len(val['UserName'].split('@'))>1):
          users_password_used_age_90.append([val['UserName']])
        count=count+1
        
    if(temp[3]!='NO_PASSWORD_CREATION_DATE'):
      if(time.strptime(temp[3],"%d-%m-%Y")<time.strptime(date_N_days_ago,"%d-%m-%Y")):
        if(len(val['UserName'].split('@'))>1):
          users_password_creation_age_90.append([val['UserName']])
        count=count+1
    
    if(count>0):
      validate=validate+1
      temp.append('IAM USER NOT FOLLING ALL RULES')
    else:
      temp.append('IAM USER FOLLING ALL RULES')
    data.append(temp)

  if(validate>0):
    if(len(non_mfa_users)>1):
      print('Follwing IAM users are not MFA users')
      for users in non_mfa_users:
        print(users[0])
      Gen_csv(non_mfa_users,'NON_MFA_USERS.csv')
      mail_function('NON_MFA_USERS.csv')
    elif(len(users_password_creation_age_90)>1):
      print('Follwing IAM users have password age more than 90 days')
      for users in users_password_creation_age_90:
        print(users[0])
      Gen_csv(users_password_creation_age_90,'IAM_USERS_PASSWORD_AGE_90_DAYS.csv')
      mail_function('IAM_USERS_PASSWORD_AGE_90_DAYS.csv')
    elif(len(users_password_used_age_90)>1):
      print('Follwing IAM users have password last used date more than 90 days')
      for users in users_password_used_age_90:
        print(users[0])
      Gen_csv(users_password_used_age_90,'IAM_USERS_PASSWORD_USED_90_DAYS.csv')
      mail_function('IAM_USERS_PASSWORD_USED_90_DAYS.csv')
  
def lambda_handler(event, context):
  main()
