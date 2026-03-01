# Makefile for minimal Django + Docker + AWS ECR + Terraform deployment
# This workflow automates:
# 1. Terraform initialization and ECR creation
# 2. Docker image build and push to ECR
# 3. EC2 creation and container run
# 4. Logs viewing
# 5. Full teardown

# Variables
REGION=eu-central-1                  # AWS region
SECRET_KEY=WyO07kprbnPrpdeDlJA5dSbAsvVygwHEjrUBjobuidoO+48/IdNCtG4XJTa5ZZNrKDw=

.PHONY: init create_ecr build push apply destroy logs clean_ecr

# 1. Terraform initialization
init:
	@echo "Initializing Terraform..."
	terraform init

# 2. Create only ECR repository
create_ecr:
	@echo "Creating AWS ECR repository only..."
	terraform apply -target=aws_ecr_repository.repo

# 3. Automatically get the ECR URL from Terraform output
ecr_url:
	@echo "Fetching ECR repository URL..."
	@terraform output -raw ecr_url

# 4. Build Docker image locally
build: ecr_url
	@echo "Building Docker image..."
	docker build -f ../Dockerfile -t django-minimal ..

# 5. Push Docker image to AWS ECR
push: build ecr_url
	@ECR_REPO=$$(terraform output -raw ecr_url); \
	echo "Logging in to AWS ECR..."; \
	aws ecr get-login-password --region $(REGION) | \
		docker login --username AWS --password-stdin $$ECR_REPO; \
	echo "Tagging Docker image..."; \
	docker tag django-minimal:latest $$ECR_REPO:latest; \
	echo "Pushing Docker image to ECR..."; \
	docker push $$ECR_REPO:latest

# 6. Apply Terraform to create EC2 and run container
apply: push
	@echo "Applying Terraform to deploy EC2 instance..."
	terraform apply -var="secret_key=$(SECRET_KEY)"

# 7. Destroy all Terraform-managed resources
destroy:
	@echo "Destroying all Terraform resources..."
	terraform destroy -auto-approve

# 8. Show logs from running Docker container on EC2
# Note: Requires SSH access or Session Manager configured
logs:
	@echo "Fetching container logs from EC2..."
	ssh ubuntu@$(PUBLIC_IP) "docker ps -q | xargs -n1 docker logs -f"

# 9. Delete all images from ECR manually (if needed before destroy)
clean_ecr:
	@echo "Deleting all images from ECR..."
	aws ecr list-images --repository-name django-minimal --query 'imageIds[*].{imageDigest:imageDigest,imageTag:imageTag}' --output text | \
		awk '{print "imageDigest="$1",imageTag="$2}' | \
		xargs -n1 aws ecr batch-delete-image --repository-name django-minimal