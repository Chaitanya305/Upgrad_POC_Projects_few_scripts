#!/bin/bash

files=("s3-schema.sql" "dynamodb-schema.sql" "ec2-schema.sql" "elb-schema.sql" "openSearch-schema.sql" "redshift-schema.sql"	"vpc-schema.sql" "cw-schema.sql" "ebs-schema.sql" "elasticache-schema.sql" "lambda-schema.sql" "rds-schema.sql")

read -p "Enter host url: " host
read -p "Enter user name:" user
read -p "Database name:" db
read -p "Password:" pass

for sql_file in "${files[@]}"; do
    echo "Running SQL script: $sql_file"
    mysql -h $host -u $user -p"$pass" $db < "$sql_file"
done

