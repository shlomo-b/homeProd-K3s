import paramiko
import time
import select
import os
import boto3
import sys
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway
import datetime

# Connect to the firewall
HOST = os.environ.get('HOST')
PORT = os.environ.get('PORT')
USERNAME = os.environ.get('USERNAME')
PASSWORD = os.environ.get('PASSWORD')
backup_file = "fortigate_backup.conf"

# AWS credentials
AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')

def get_full_configuration():
    try:
        print(f"Connecting to: {HOST}:{PORT}...")

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(HOST, PORT, USERNAME, PASSWORD, timeout=10, allow_agent=False, look_for_keys=False)

        shell = ssh.invoke_shell()
        time.sleep(1)
        shell.recv(65535)
        print(f"✅ The user successfully connected to: {'Fortigate'}")
        print("Command:📤 show full-configuration")
        shell.send("show full-configuration\n")

        with open(backup_file, 'w') as f:
            while True:
                rlist, _, _ = select.select([shell], [], [], 1)
                if shell in rlist:
                    chunk = shell.recv(99999).decode(errors='replace')
                    if "--More--" in chunk:
                        shell.send(" ")
                        chunk = chunk.replace("--More--", "")

                    f.write(chunk)
                    f.flush()

                    if "FW-Shlomi #" in chunk:
                        break

        print(f"✅ Configuration saved to: {backup_file}")
        ssh.close()
        return True

    except Exception as e:
        print(f" Error: ❌ {e}")
 
# Function to upload the backup file to S3
def backup_data():
    try:
        # Check if the file exists
        if not os.path.exists(backup_file):
            print(f"❌ Backup file '{backup_file}' not found.")
            return

        # Define S3 bucket details
        BUCKET_NAME = os.environ.get('BUCKET_NAME')
        s3_object_name = f"backups/{backup_file}"

        # Create a Boto3 S3 client
        s3 = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)

        # Upload the file to S3
        s3.upload_file(backup_file, BUCKET_NAME, s3_object_name)
        print(f"✅ Backup file: {backup_file}, successfully uploaded to S3 bucket: {BUCKET_NAME}")

    except Exception as e:
        print(f"❌ Error during S3 upload: {e}")


def push_metrics(success: bool, duration_seconds: float):
    try:
        registry = CollectorRegistry()
        status = Gauge('fortigate_backup_success', '1 if successful, 0 if failed', registry=registry)
        duration = Gauge('fortigate_backup_duration_seconds', 'How long the backup took', registry=registry)
        timestamp = Gauge('fortigate_backup_last_run_timestamp', 'When backup was run (unix)', registry=registry)

        status.set(1 if success else 0)
        duration.set(duration_seconds)
        timestamp.set(int(datetime.datetime.utcnow().timestamp()))

        pushgateway_url = os.getenv("PUSHGATEWAY_URL", "http://pushgateway:9091")
        push_to_gateway(pushgateway_url, job='fortigate-backup', registry=registry)
        print("📤 Metrics pushed to Pushgateway successfully.")
    except Exception as e:
        print(f"❌ Failed to push metrics: {e}")

if __name__ == "__main__":
    start_time = time.time()
    result = get_full_configuration()
    if result:
        backup_data()
    else:
        print("❌ Configuration retrieval failed. Skipping S3 upload.")
    elapsed = time.time() - start_time
    push_metrics(result, elapsed)
