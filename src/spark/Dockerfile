# 1. Use the official EMR Serverless image
FROM public.ecr.aws/emr-serverless/spark/emr-7.0.0:latest

# 2. Switch back to the EMR user for security
USER hadoop:hadoop

# 3. Copy the script (the directory is now safe to write to and read from)
COPY --chown=hadoop:hadoop raw_to_iceberg.py /home/hadoop/raw_to_iceberg.py
