import boto3
from datetime import datetime, timedelta, timezone

s3 = boto3.client('s3')

incomplete_object = {}
all_buckets = []
non_multipart_object_buckets = []

def size_of_parts(bucket_name, key, upload_id, threshold):
    try:
        response = s3.list_parts(Bucket = bucket_name, Key = key, UploadId = upload_id)
        total_size = 0
        if 'Parts' in response:
            for part in response['Parts']:
                total_size += part['Size']
                if total_size >= threshold:
                    return True
        
        return False
    except:
        print("Error occurred while listing parts")



def list_all_buckets():
    global all_buckets
    response = s3.list_buckets()
    for bucket_name in response['Buckets']:
        all_buckets.append(bucket_name['Name'])
    print(len(all_buckets))

def s3_check():
    global incomplete_object
    global all_buckets
    global non_multipart_object_buckets
    count = 0
    current_time = datetime.now(timezone.utc)
    cutoff_time = current_time - timedelta(days=7)
    #listing all buckets
    print('Listing all buckets', list_all_buckets())
    for bucket in all_buckets:
        count +=1
        print(' checking for bucket :-', bucket)
        try:
            multipart_data = s3.list_multipart_uploads(Bucket = bucket, MaxUploads = 1000)
            if 'Uploads' in multipart_data:
                upload_keys = []
                # non_multipart_object_buckets.remove(bucket)
                for upload in multipart_data['Uploads']:
                    # Check if the upload creation date is older than 7 days
                    if upload['Initiated'] < cutoff_time:
                        #minimum size threshold for identifying incomplete
                        if size_of_parts(bucket, upload['Key'], upload['UploadId'], 1073741824):
                            upload_keys.append(upload['Key'])
                            incomplete_object[bucket] = upload_keys
                            if bucket in all_buckets:
                                all_buckets.remove(bucket)
        except Exception as e:
            print('error occured at calling list multipart bucket for', bucket, e)
        
    
    print('******************* s3 bucket Final output is ***********************')
    print("incomplete Multipart object buckets are:", incomplete_object)
    print('total bucket we have:', count)
 
