aws s3api create-bucket \
--bucket bape-tf-state-davidg-2026 \
--create-bucket-configuration LocationConstraint=eu-central-1

aws s3api put-bucket-versioning \
--bucket bape-tf-state-davidg-2026 \
--versioning-configuration Status=Enabled

aws s3api put-public-access-block \
--bucket bape-tf-state-davidg-2026 \
--public-access-block-configuration file://src/public-access-block-config.json
