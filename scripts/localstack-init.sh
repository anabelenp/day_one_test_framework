#!/bin/bash

# LocalStack Initialization Script for Day-1 Framework
echo "🚀 Starting LocalStack initialization..."

# Wait for LocalStack to be ready
echo "⏳ Waiting for LocalStack to be ready..."
until curl -s http://localhost:4566/health > /dev/null; do
    echo "Waiting for LocalStack..."
    sleep 2
done

echo "✅ LocalStack is ready!"

# Create S3 buckets
echo "📦 Creating S3 buckets..."
awslocal s3 mb s3://netskope-test-bucket || echo "Bucket already exists"
awslocal s3 mb s3://netskope-logs-bucket || echo "Bucket already exists"

# Create DynamoDB tables
echo "🗄️ Creating DynamoDB tables..."
awslocal dynamodb create-table \
    --table-name netskope-test-table \
    --attribute-definitions AttributeName=id,AttributeType=S \
    --key-schema AttributeName=id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region us-east-1 || echo "Table already exists"

# Create SQS queues
echo "📬 Creating SQS queues..."
awslocal sqs create-queue --queue-name netskope-test-queue || echo "Queue already exists"

# Create SNS topics
echo "📢 Creating SNS topics..."
awslocal sns create-topic --name netskope-test-topic || echo "Topic already exists"

echo "🎉 LocalStack initialization completed successfully!"