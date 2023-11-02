# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import os
import random
import string
from datetime import datetime

import boto3

REGION = os.environ.get('AWS_REGION')
session = boto3.Session(region_name=REGION)
sts = session.client('sts')
AWS_ID = sts.get_caller_identity().get('Account')


OUTPUT_BUCKET = 'comprehend-semi-structured-docs-{}-{}'.format(REGION, AWS_ID)
PRELABELING_FOLDER = 'prelabeling'

def get_random_string(length):
    return "".join(
        random.choice(string.ascii_lowercase + string.digits) for i in range(length)
    )

s3_client = boto3.client('s3')

def lambda_handler(event, context):

    now = datetime.now() # current date and time

    prefix =  event['prefix']
    date_time = now.strftime("%Y-%m-%d-%H-%M")
    
    execution_id = prefix + "-" +date_time + '-' + get_random_string(4)
    
    premanifest_source_bucket = event['premanifest']['bucket']
    premanifest_source_key = event['premanifest']['key']
    
    premanifest_file_name = premanifest_source_key.split('/')[-1]
    
    premanifest_source = '{}/{}'.format(premanifest_source_bucket,premanifest_source_key)
    
    premanifest_destination_key ='{}/{}/input-premanifest/{}'.format(PRELABELING_FOLDER,execution_id,premanifest_file_name)
    
    
    
    response = s3_client.copy_object(
        Bucket=OUTPUT_BUCKET,
        Key=premanifest_destination_key,
        CopySource=premanifest_source
    )
    print('Copied pre-manifest file to {}'.format(premanifest_destination_key))
        
    return {
        "statusCode":200,
        "execution_id" : execution_id
    }