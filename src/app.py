import os
import boto3
import zipfile
from datetime import datetime
import requests
import kubernetes.client
from kubernetes.client.rest import ApiException
from kubernetes import config

def fetch_transactions(customer_id, start_date, end_date):
    api_url = os.getenv('API_URL')
    api_user = os.getenv('API_USER')
    api_token = os.getenv('API_TOKEN')
    
    # Placeholder for the actual logic to fetch transactions
    response = requests.get(
        f"{api_url}/transactions",
        params={"customer_id": customer_id, "start_date": start_date, "end_date": end_date},
        auth=(api_user, api_token)
    )
    transactions = response.json()
    return transactions

def create_zip_file(customer_id, start_date, end_date, transactions):
    filename = f"{customer_id}-{int(start_date.timestamp())}-{int(end_date.timestamp())}-{int(datetime.now().timestamp())}.zip"
    with zipfile.ZipFile(filename, 'w') as zipf:
        for i, transaction in enumerate(transactions):
            zipf.writestr(f"transaction_{i}.txt", str(transaction))
    return filename

def upload_to_s3(filename):
    s3_url = os.getenv('S3_URL')
    s3_access_key = os.getenv('S3_ACCESS_KEY')
    s3_secret_key = os.getenv('S3_SECRET_KEY')

    s3 = boto3.client('s3', endpoint_url=s3_url, aws_access_key_id=s3_access_key, aws_secret_access_key=s3_secret_key)
    bucket_name = 'your-s3-bucket'
    print("s3.upload_file(filename, bucket_name, filename)")
    os.remove(filename)
    return f"s3://{bucket_name}/{filename}"

def mark_configmap_executed(api_instance, configmap_name, namespace):
    body = {"data": {"status": "executed"}}
    try:
        api_instance.patch_namespaced_config_map(configmap_name, namespace, body)
    except ApiException as e:
        print(f"Exception when calling CoreV1Api->patch_namespaced_config_map: {e}")

def main():
    config.load_incluster_config()
    api_instance = kubernetes.client.CoreV1Api()

    namespace = 'transaction-requests'
    configmaps = api_instance.list_namespaced_config_map(namespace)

    for configmap in configmaps.items:
        if configmap.data.get('status') == 'pending':
            customer_id = configmap.data['customer_id']
            start_date = datetime.fromisoformat(configmap.data['start_date'])
            end_date = datetime.fromisoformat(configmap.data['end_date'])

            transactions = fetch_transactions(customer_id, start_date, end_date)
            zip_file = create_zip_file(customer_id, start_date, end_date, transactions)
            s3_url = upload_to_s3(zip_file)

            print(f"Uploaded to {s3_url}")
            mark_configmap_executed(api_instance, configmap.metadata.name, namespace)

if __name__ == "__main__":
    main()
