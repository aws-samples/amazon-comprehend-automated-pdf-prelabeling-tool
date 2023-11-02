# Pre-Labeling Tool

There are 2 different versions of the **Pre-Labeling Tool**:
- Fuzzy Matching version
- Comprehend version


## Fuzzy Matching Version

### Presentation
The Fuzzy Matching version uses [Fuzzy Matching](https://en.wikipedia.org/wiki/Approximate_string_matching) to detect the expected entities provided by the user and generate the pre-annotations.
This Fuzzy Matching version can be used to directly train a Comprehend Custom Entity Recognizer and/or create a Ground Truth Labeling Job that human annotators can use to review the generated pre-anotations before training a model.

Concretly, these are the inputs of this Pre-Labeling Tool:

- PDF documents
![PDF](/Pre_labeling_tool/img/raw_pdf.png)

- 1 **expected_entities** file per pdf. 
    
    These files contain the words that the tool will look for in the document to pre-annotate it. This file has the following content format:

  ```
  [
      {
          "expected_texts": [
              "AnyCompany Finance Ltd"
          ],
          "entity_type": "bank_name",
          "ignore_list": []
      },
      {
          "expected_texts": [
              "MARTHA RIVERA"
          ],
          "entity_type": "customer_name",
          "ignore_list": []
      },
      ...
  ]
  ```
  For more details on this file and its format, please have a look at the notebook [```generate_premanifest_file.ipynb```](Pre_labeling_tool/notebooks/generate_premanifest_file.ipynb).



- 1 **premanifest** file (```premanifest.json```)
  This file maps each one of the PDF documents with its expected_entities file. It has the following content format:
  ```
  [
      {
          "pdf": "s3://comprehend-semi-structured-docs-REGION-ACCOUNT_ID/prelabeling-inputs/example-demo/pdf/bank_stmt_0.pdf",
          "expected_entities": "s3://comprehend-semi-structured-docs-REGION-ACCOUNT_ID/prelabeling-inputs/example-demo/expected-entities/file_bank_stmt_0.json"
      },
      ...
  ]
  ```


Note: in [generate_premanifest_file.ipynb](Pre_labeling_tool/notebooks/generate_premanifest_file.ipynb), we show how to create these files (expected_entities.json and premanifest.json) from a CSV file (called **Entity list document**) like the following one:
![Entity list](/Pre_labeling_tool/img/entity_list.png)


The Pre-Labeling Tool will use those inputs to annotate the documents with their corresponding entities. Using these automatically generated pre-annotations, the Pre-Labeling Tool can directly train a Comprehend Custom Entity Recognizer and/or create a Ground Truth Labeling Job that human annotators can use to review the generated pre-anotations before training a model. As shown in the screenshot below, this will significantly reduce the manual labor by the annotators as the displayed annotations make it easier to fully annotate the documents.
![Ground Truth Labeling Job](/Pre_labeling_tool/img/gt_labeling_job.png)


### Technical description
This Fuzzy Matching Version corresponds to the Step Functions called ```PrelabelingFuzzyMatchingStepFunctions``` in the ```Pre_labeling_tool/pre_labeling_tool_template.yaml``` stack. 

The workflow is the following:
![Fuzzy Matching workflow](/Pre_labeling_tool/img/fuzzymatching_workflow.png)


The different steps are the following:
- `Create execution id` : Lambda function that generates a unique execution id that will be used to save outputs to s3
- `Map`: Step Functions Map State that runs Lambda functions (`prelabeling_execute_preannotation_jobs_mapstate`) in parrallel in order to generate the pre-annotations. For each document, the Lambda function will first call Textract to perform OCR and extract all text of the file. This output will then be separated in its pages and annotations will be generated for each page using Fuzzy Matching algorithm. 
  
  Note: this Fuzzy Matching is not a simple exact text matching but has tunable parameters that allows user to do approximative text matching  (and account for spedlling mistakes for example).


- `Merge individual annotation files`: Lambda function that merges the invididual annotation files generated at previous Map step and creates the final manifest file.
- `Create GT Labeling Job` [optional]: Lambda function that will create the GT Labeling Job. This step is optional.
- `Create Comprehend model` [optional]: uses the manifest file created by the `Merge individual annotation files` and adapt its format in order to directly train a custom Entity Recognizer Comprehend model.

## Comprehend Version

### Presentation
The Comprehend version requires that you already have trained a Custom Entity Recognizer Comprehend model. It will then use this model to pre-annotate the PDF documents.

This Comprehend version can be used to create a Ground Truth Labeling Job.

For this Comprehend version, the only required inputs are:
- an already trained Custom Entity Recognizer Comprehend model
- PDF documents
Note that in that case, the user doesn't need to provide expected entities.

### Technical description

The workflow is the following:

![Comprehend workflow](/Pre_labeling_tool/img/comprehend_workflow.png)


These are the different steps of this Comprehend Version Step Functions:
- `Create execution id` : Lambda function that generates a unique execution id that will be used to save outputs to s3
- `Comprehend Batch Prediction`: Lambda function that runs batch asynchronous inference using Comprehend model to detect the entities on the PDF documents
- `Comprehend Check Completion`: Lambda function that checks the completion of the Comprehend asynchronous batch inference.
- `Combine outputs`: Lambda function that post-processes (i.e. unzips and merges) Comprehend async batch prediction outputs
- `Write Manifest`: Lambda function that writes the final manifest file
- `Create GT Labeling Job`: Lambda function that creates the GT Labeling Job

## How to use this Pre-Labeling Tool?

### Step 1: Prepare the inputs required

The notebook ```Pre_labeling_tool/notebooks/generate_premanifest_file.ipynb``` shows how to prepare these inputs for a public dataset of fake PDF documents.

More specifically, it shows how to create the expected entities JSON files and the pre-manifest file required by the Pre-Labeling Tool using an Entity list document provided by the user.

You can run this notebook in SageMaker Studio. Please make sure to add s3 permissions to the role associated with the notebook.
After running the notebook, check if all inputs have been correctly saved in s3. We recommend using the following hierarchy:
```
└── comprehend-semi-structured-docs-{region-name}-{account-id}
    └── prelabeling-inputs
        └── example-demo # custom project name
            ├── pdf/
            │   ├── file_1.pdf
            │   ├── file_2.pdf
            │   └── ...
            ├── expected-entities/
            │   ├── file_1.json
            │   ├── file_2.json
            │   └── ...
            └── premanifest/
                └── premanifest.json
```

### Step 2: Start the Step Function execution

You can use the notebook ```Pre_labeling_tool/notebooks/start_step_functions.ipynb``` to start the Pre-Labeling Tool.
Explanations about the input event and all its parameters are given in the notebook.


### Step 3: Inspect the outputs

- Review the outputs saved in s3
  The outputs generated by the Pre-Labeling Tool will be saved with the following hierarchy:

  For Fuzzy Matching version:
  ```
  └── comprehend-semi-structured-docs-{region-name}-{account-id}
      └── prelabeling
          └── {prefix}+{datetime} # unique folder per job
              ├── consolidated_manifest/
              │   └── consolidated_manifest_comprehend.manifest # manifest file that can be used to train Comprehend
              │   └── consolidated_manifest.manifest # manifest file used by GT Labeling Job
              ├── input-premanifest/
              │   └── premanifest.json # copy of the pre-manifest file used as input
              ├── temp_individual_manifests/ # individual manifest per doc per page
              │   ├── file_1_page_0_manifest.manifest 
              │   ├── file_1_page_1_manifest.manifest
              │   └── ...
              └── textract-annotations/ # textract outputs
  ```

  For Comprehend version:
  ```
  └── comprehend-semi-structured-docs-{region-name}-{account-id}
      └── prelabeling
          └── {prefix}+{datetime} # unique folder per job
              ├── consolidated_manifest/
              │   └── final-manifest.manifest # manifest file used by GT Labeling Job
              ├── input-premanifest/
              │   └── premanifest.json # copy of the pre-manifest file used as input
              ├── comprehend-annotations/
              │   ├── zipped_files/ # comprehend async output
              │   ├── unzipped_files/ # comprehend async output unzipped
              │   │   ├── success/
              │   │   └── failure/
              │   ├── labeling-annotation-folder/  
              │   │   ├── file_1_page_0.json # Comprehend pre-annotations
              │   │   ├── ...
              │   │   └── blocks/ # Textract outputs
              │   └── manifest/
              │       └── manifest.csv # intermediate manifest file
              └── input-comprehend-pdf-batches/ # copy of PDF files grouped in batches
                  ├── batch-0/
                  │   ├── file_1.pdf
                  │   ├── ...
                  │   └── file_500.pdf
                  └── ...
  ```

- Open the GT Labeling Job that was created to review the annotations (optional step)

- Use the custom model that was trained by Comprehend (optional step)

# FAQ

## How to speed-up the Map state in the Fuzzy Matching version?

The concurrency limit for the Map State has been set to 2 (default is 1000) because of Textract Quotas. By default, there are the following quotas:
- ```StartDocumentTextDetection throttle limit in transactions per second``` quota is 2 per second 
- ```Async DocumentTextDetection throttle limit``` for max number of concurrent jobs is 500 max. 

Hence we might exceed this threshold if we launch too many Lambdas in parrallel. 
If you want to increase the number of parrallel lambdas to increase the speed of the Map state, you first need to ask for Quota increase.

## How to deploy the stack?

This Pre-Labeling Tool is part of a nested stack defined in ```template.yaml```.
It is necessary to deploy at least once the whole stack as explained in [README.md](README.md). Indeed, the Pre-Labeling Tool rely on some resources defined in (comprehend-semi-structured-documents-annotation-template.yml)[comprehend-semi-structured-documents-annotation-template.yml]. 


If you want to re-deploy only some resources that are specific to the Pre-labeling Tool, please go to ```Pre_labeling_tool/``` folder and run:

```
sam build -t pre_labeling_tool_template.yaml

sam deploy --parameter-overrides SemiStructuredDocumentsS3Bucket=REPLACE_WITH_BUCKET_NAME SemiStructuredDocumentsS3BucketArn=REPLACE_WITH_ARN StackComprehendSemiStructuredDocAnnotation=REPLACE_WITH_ARN --capabilities CAPABILITY_AUTO_EXPAND CAPABILITY_NAMED_IAM --guided
```

# License

All files outside of the `Pre-labeling_tool/` folder and inside the `Pre_labeling_tool/src/lambda/code/prelabeling_create_gt_labeling_job/ui-template/` are licensed under the Apache License. See the `LICENSE` file.

All other files are licensed under the MIT-0 License. See the `Pre_labeling_tool/LICENSE` file.