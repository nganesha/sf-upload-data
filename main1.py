import os
import base64
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
from simple_salesforce import Salesforce

# Initialize Salesforce connection
sf = Salesforce(username='your_username', password='your_password', security_token='your_security_token')

def upload_file_to_salesforce(new_case_id, file_path, file_name):
    """
    Upload a file to Salesforce using ContentVersion and link it to a case using ContentDocumentLink.
    """
    try:
        # Read file content and encode in Base64
        with open(file_path, "rb") as file:
            file_content = base64.b64encode(file.read()).decode("utf-8")
        
        # Step 1: Upload file to ContentVersion
        content_version = {
            "Title": file_name,
            "PathOnClient": file_name,
            "VersionData": file_content
        }
        content_version_response = sf.ContentVersion.create(content_version)
        content_document_id = content_version_response["id"]

        # Step 2: Link file to the case using ContentDocumentLink
        content_document = sf.query(
            f"SELECT ContentDocumentId FROM ContentVersion WHERE Id = '{content_document_id}'"
        )
        if content_document["records"]:
            document_id = content_document["records"][0]["ContentDocumentId"]

            content_document_link = {
                "ContentDocumentId": document_id,
                "LinkedEntityId": new_case_id,
                "ShareType": "V",  # Viewer permission
                "Visibility": "AllUsers"
            }
            sf.ContentDocumentLink.create(content_document_link)
            print(f"File '{file_name}' successfully uploaded and linked to Case {new_case_id}")
        else:
            print(f"Failed to retrieve ContentDocumentId for {file_name}")

    except Exception as e:
        print(f"Error uploading file '{file_name}' to case {new_case_id}: {str(e)}")


def process_case(old_case_id, new_case_id, attachments_df):
    """
    Process a single case and upload its attachments sequentially.
    """
    case_attachments = attachments_df[attachments_df["Old_Case_Id"] == old_case_id]

    for _, attachment in case_attachments.iterrows():
        file_name = attachment["file_names"]
        file_path = os.path.join("path_to_attachments_directory", file_name)  # Update the path

        if os.path.exists(file_path):
            upload_file_to_salesforce(new_case_id, file_path, file_name)
        else:
            print(f"File not found: {file_path}")


def upload_attachments(file1_path, file2_path):
    """
    Main function to read input files and upload attachments to Salesforce.
    """
    # Read input files
    file1 = pd.read_csv(file1_path)
    file2 = pd.read_csv(file2_path)

    # Filter cases with attachments
    cases_with_attachments = file1[file1["Old_case_has_attachment"] == True]

    # Use ThreadPoolExecutor to process cases in parallel
    with ThreadPoolExecutor(max_workers=5) as executor:
        for _, case_row in cases_with_attachments.iterrows():
            old_case_id = case_row["Old_Case_id"]
            new_case_id = case_row["New_Case_Id"]

            executor.submit(process_case, old_case_id, new_case_id, file2)


# Paths to input files
file1_path = "path_to_file1.csv"
file2_path = "path_to_file2.csv"

# Start the upload process
upload_attachments(file1_path, file2_path)
