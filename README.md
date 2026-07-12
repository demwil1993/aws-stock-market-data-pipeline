## Deployment

This project uses AWS SAM for infrastructure deployment.

### Prerequisites

- AWS CLI
- AWS SAM CLI
- Python 3.12
- An AWS CLI profile with deployment permissions
- A Twelve Data API key stored in AWS Secrets Manager

### Configure SAM

Copy the example configuration:

```cmd
copy infrastructure\samconfig.example.toml infrastructure\samconfig.toml