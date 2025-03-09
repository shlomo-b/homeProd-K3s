import paramiko
import time
import select
import os
import boto3
import re

# Connect to the switch
HOST = os.environ.get('HOST')
PORT = os.environ.get('PORT')
USERNAME = os.environ.get('USERNAME')
PASSWORD = os.environ.get('PASSWORD')
backup_file = "juniper_backup.txt"

# AWS credentials
AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')


def get_full_configuration():
    try:
        print(f"Connecting to: {HOST}:{PORT}...")

        # Initialize SSH Client
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(HOST, PORT, USERNAME, PASSWORD, timeout=10, allow_agent=False, look_for_keys=False)

        # Open an interactive shell
        shell = ssh.invoke_shell()
        time.sleep(2)
        shell.recv(65535)

        # Enter CLI mode
        print(f"✅ The user successfully connected to: {'Juniper_BB'}")
        shell.send("cli\n")
        time.sleep(1)
        shell.recv(65535)

        shell.send("set cli screen-length 0\n")
        time.sleep(1)
        shell.recv(65535)

        # Send the main command
        shell.send("show configuration | display set\n")
        time.sleep(3)

        output = ""

        with open(backup_file, 'w') as f:
            while True:
                rlist, _, _ = select.select([shell], [], [], 3)
                if shell in rlist:
                    chunk = shell.recv(99999).decode(errors='replace')

                    # Remove extra spaces and empty lines
                    chunk = re.sub(r' +', ' ', chunk)
                    chunk = chunk.strip()
                    chunk = "\n".join(
                        [line.strip() for line in chunk.split("\n") if line.strip()])

                    output += chunk + "\n"
                    f.write(chunk + "\n")
                    f.flush()

                    # Exit when CLI prompt appears again (root@Juniper_BB>)
                    if "root@Juniper_BB>" in chunk or "root@Juniper_BB#" in chunk:
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


if __name__ == "__main__":
    if get_full_configuration():
         backup_data()
    else:
        print("❌ Configuration retrieval failed. Skipping S3 upload.")