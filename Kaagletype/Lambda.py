import os
import boto3
import time
import json
sagemaker = boto3.client('sagemaker')
start_time = time.time()
def lambda_handler(event, context):
    INSTANCE_TYPE = event['INSTANCE_TYPE']
    NOTEBOOK_NAME = event['NOTEBOOK_NAME']
    ROLE=event['ROLE']
    name = NOTEBOOK_NAME +'-'+str(int(time.time()))
    
    Sagemaker_notebook = sagemaker.create_notebook_instance(NotebookInstanceName = name,InstanceType = INSTANCE_TYPE,RoleArn=ROLE)
    
    status ='Pending'
    while status == 'Pending' and start_time < 0.29:
      time.sleep(5)
      response = sagemaker.describe_notebook_instance(NotebookInstanceName=name)
      status = response['NotebookInstanceStatus']
    
    if status == 'InService':
      response = sagemaker.create_presigned_notebook_instance_url(NotebookInstanceName= name)
      return {'NotebookURL': response['AuthorizedUrl']}
    else:
      return {'Notebook status':status,'Name': name}
