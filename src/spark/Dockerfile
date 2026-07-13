# 1. Use the official EMR Serverless image
FROM public.ecr.aws/emr-serverless/spark/emr-7.0.0:latest

# 2. Switch to root to configure the filesystem
USER root

# 3. Explicitly create the directory and give the hadoop user full ownership
RUN mkdir -p /app && chown -R hadoop:hadoop /app

# 4. Switch back to the EMR user for security
USER hadoop:hadoop

# 5. Copy the script (the directory is now safe to write to and read from)
COPY --chown=hadoop:hadoop raw_to_iceberg.py /app/raw_to_iceberg.py

# 6. Set the working directory
WORKDIR /app