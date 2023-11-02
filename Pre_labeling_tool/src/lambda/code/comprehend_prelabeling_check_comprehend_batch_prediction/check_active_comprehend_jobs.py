# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import boto3


def check_comprehend_jobs_finished(job_ids, region):
    """
    This function takes a list of job_ids and checks if they are all finished.
    If they are all finished, it returns True.
    If not, it returns False.
    If there is an error in one of the jobs, it returns the error message.

    job_ids: list of job_ids
    region: the region where the jobs are running

    returns: True, False, or error message

    Example:
    check_comprehend_jobs_finished(['job1','job2'],'us-east-1')
    returns: True or False

    Example:
    check_comprehend_jobs_finished(['job1','job2'],'us-east-1')
    returns: "error in job job1"
    """

    comprehend_client = boto3.client("comprehend", region_name=region)
    all_finished = True
    for job_id in job_ids:
        response = comprehend_client.describe_entities_detection_job(JobId=job_id)
        job_status = response["EntitiesDetectionJobProperties"]["JobStatus"]
        if job_status in ["SUBMITTED", "IN_PROGRESS"]:
            all_finished = False
        elif job_status in ["FAILED", "STOP_REQUESTED", "STOPPED"]:
            all_finished = "error in job {}".format(job_id)
            if 'Message' in response['EntitiesDetectionJobProperties'].keys():
                error_msg = response['EntitiesDetectionJobProperties']['Message']
                print(error_msg)
                all_finished = all_finished + '-' + error_msg
            else:
                print('no error Message in response')

    return all_finished
