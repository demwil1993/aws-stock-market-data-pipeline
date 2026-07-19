```
aws-stock-market-data-pipeline/
│
├── README.md
├── LICENSE
├── .gitignore
├── .env.example
├── environment.yml
├── requirements.txt
├── pytest.ini
│
├── architecture/
│   ├── architecture-diagram.png
│   └── data-flow.md
│
├── docs/
│   ├── architecture-decisions.md
│   ├── data-dictionary.md
│   └── deployment-guide.md
│
├── infrastructure/
│   ├── template.yaml
│   ├── samconfig.example.toml
│   └── samconfig.toml
│
├── scripts/
│   ├── run_local.py
│   └── run_lambda_local.py
│
├── sql/
│   ├── analytics_queries.sql
│   └── validation_queries.sql
│
├── src/
│   ├── requirements.txt
│   │
│   └── stockpipeline/
│       ├── __init__.py
│       ├── logging_config.py
│       │
│       ├── ingestion/
│       │   ├── __init__.py
│       │   ├── api_client.py
│       │   ├── config.py
│       │   ├── exceptions.py
│       │   ├── lambda_function.py
│       │   ├── models.py
│       │   ├── pipeline.py
│       │   ├── validation.py
│       │   └── watchlist.py
│       │
│       ├── storage/
│       │   ├── __init__.py
│       │   ├── local_storage.py
│       │   └── s3_storage.py
│       │
│       └── transformation/
│           ├── __init__.py
│           └── standardized_to_curated.py
│
└── tests/
    ├── test_api_client.py
    ├── test_lambda_function.py
    ├── test_local_storage.py
    ├── test_models.py
    ├── test_pipeline.py
    ├── test_s3_storage.py
    └── test_validation.py
```