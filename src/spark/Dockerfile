# Use the official AWS EMR Serverless Spark image
FROM public.ecr.aws/emr-serverless/spark/emr-7.0.0:latest

USER root
# Install any additional pure-Python dependencies your pipeline might need later
# RUN pip3 install boto3 pydantic

# Switch back to the required non-root EMR user
USER hadoop:hadoop

# Copy your enterprise PySpark script into the container
COPY --chown=hadoop:hadoop raw_to_iceberg.py /app/raw_to_iceberg.py

# Set the working directory
WORKDIR /app