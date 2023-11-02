import json

def get_all_s3_objects(s3_client, bucket, key, file_format='.manifest'):
    '''Get the full list of files'''
    list_files = []
    continuation_token = None
    while True:
        arg_dict = {'Bucket':bucket, 'Prefix':key}
        if continuation_token:
            arg_dict['ContinuationToken'] = continuation_token
        response = s3_client.list_objects_v2(**arg_dict)
        contents = response.get('Contents')
        if contents is None:
            return list_files
        else:
            list_files += [obj['Key'] for obj in contents if obj['Key'].endswith(file_format)]
        if not response.get('IsTruncated'):
            return list_files
        continuation_token = response.get('NextContinuationToken')

def generate_pre_manifest_file(pdf_s3uri,expected_entities_s3uri,pre_manifest_s3_path,s3_client):
    """Generates a pre-manifest file used as an input for the pre-labeling pipeline

    Args:
        pdf_s3uri (string): s3 folder where the pdf documents are stored
        expected_entities_s3uri (string): s3 folders where the expected entities documents are stored
        s3_client: s3_client

    Returns:
        pre_manifest_list: pre manifest file
    """

    pre_manifest = []
    
    expected_entity_extension = '.json'
    pdf_s3uri_bucket, pdf_s3uri_folder = split_s3_uri(pdf_s3uri)

    pdf_keys = get_all_s3_objects(s3_client, pdf_s3uri_bucket, pdf_s3uri_folder,'.pdf')
    print('Found {} pdf documents in {}'.format(len(pdf_keys),pdf_s3uri))
    
    expected_entities_bucket, expected_entities_folder = split_s3_uri(expected_entities_s3uri)
    expected_entities_keys = get_all_s3_objects(s3_client, expected_entities_bucket, expected_entities_folder,expected_entity_extension)
    print('Found {} expected_entities json documents in {}'.format(len(expected_entities_keys),expected_entities_s3uri))

    for pdf_key in pdf_keys:
        for expected_entities_key in expected_entities_keys:
            # print(pdf_key.split('/')[-1].split('.pdf')[0])
            # print(expected_entities_key.split('/')[-1].split(expected_entity_extension)[0])
            if pdf_key.split('/')[-1].split('.pdf')[0] == expected_entities_key.split('/')[-1].split(expected_entity_extension)[0]:
                pre_manifest.append({'pdf':'s3://{}/{}'.format(pdf_s3uri_bucket,pdf_key),'expected_entities':'s3://{}/{}'.format(expected_entities_bucket,expected_entities_key)})
    
    print('Found {} matches between pdf and expected_entities file names'.format(len(pre_manifest)))
    
    pre_manifest_bucket, pre_manifest_key = split_s3_uri(pre_manifest_s3_path)
    response = s3_client.put_object(Body=json.dumps(pre_manifest), Bucket=pre_manifest_bucket, Key=pre_manifest_key)

    if response['ResponseMetadata']['HTTPStatusCode']==200:
        print('Successfully save pre_manifest file in s3://{}/{}'.format(pre_manifest_bucket,pre_manifest_key))

    return pre_manifest


def split_s3_uri(uri):
    """return (bucket, key) tuple from s3 uri like 's3://bucket/prefix/file.txt' """
    return uri.replace('s3://','').split('/',1)
'''
def list_object_with_extension(s3_uri,extension,s3_client):
    """list objects with a given extension in a given s3 folder

    Args:
        s3_uri (str): s3 uri where to list the files from
        extension: only files with this extension will be counted

    Returns:
        list_objs: list of files keys in the given s3_uri with the given extension  
    """
    bucket,prefix=split_s3_uri(s3_uri)
    response = s3_client.list_objects(
        Bucket=bucket,
        Prefix=prefix,
    )
    list_objs = [obj['Key'] for obj in response['Contents'] if obj['Key'].endswith(extension)]
    return bucket,list_objs
'''


def extract_some_stack_resources(stack_name,client_cloudformation):
    # DEPRECATED
    """Extract the Bucket name created by the ComprehendSemiStructuredDocAnnotation stack and the Step Function arn created by the stack PrelabelingTool

    Args:
        stack_name (string): Name of the parent CF Stack
        client_cloudformation 

    Returns:
        SemiStructuredDocumentsS3Bucket: SemiStructuredDocumentsS3Bucket name created by ComprehendSemiStructuredDocAnnotation CF stack
        PrelabelingStepFunctionsArn: Arn of the Prelabeling Step Function created by PrelabelingTool CF stack
    
    Note: this function assumes that the name of the children stacks were not changed. but kept at their original value (i.e. ComprehendSemiStructuredDocAnnotation and PrelabelingTool)
    """
    # Child stacks name given in the parent CF template
    ComprehendSemiStructuredDocAnnotation_stack_name = 'ComprehendSemiStructuredDocAnnotation'
    PrelabelingTool_stack_name = 'PrelabelingTool'

    # List the 2 children stacks created by parent stack
    child_stacks = client_cloudformation.list_stack_resources(
        StackName=stack_name
        )['StackResourceSummaries']

    # Find child stacks ResourceId
    for child_stack in child_stacks:
        if child_stack['LogicalResourceId']==ComprehendSemiStructuredDocAnnotation_stack_name:
            ComprehendSemiStructuredDocAnnotation_stack = child_stack
        elif child_stack['LogicalResourceId']==PrelabelingTool_stack_name:
            PrelabelingTool_stack = child_stack

    # Extract SemiStructuredDocumentsS3Bucket
    ComprehendSemiStructuredDocAnnotation_stack_outputs = client_cloudformation.describe_stacks(
        StackName=ComprehendSemiStructuredDocAnnotation_stack['PhysicalResourceId']
    )['Stacks'][0]['Outputs']
    for output in ComprehendSemiStructuredDocAnnotation_stack_outputs:
        if output['OutputKey']=='SemiStructuredDocumentsS3Bucket':
            SemiStructuredDocumentsS3Bucket = output['OutputValue']
    print('Bucket: {}'.format(SemiStructuredDocumentsS3Bucket))
    
    # Extract PrelabelingStepFunctionsArn
    PrelabelingTool_stack_outputs = client_cloudformation.describe_stacks(
        StackName=PrelabelingTool_stack['PhysicalResourceId']
    )['Stacks'][0]['Outputs']
    for output in PrelabelingTool_stack_outputs:
        if output['OutputKey']=='PrelabelingStepFunctionsArn':
            PrelabelingStepFunctionsArn = output['OutputValue']
    print('Step Function: {}'.format(PrelabelingStepFunctionsArn))

    return SemiStructuredDocumentsS3Bucket, PrelabelingStepFunctionsArn