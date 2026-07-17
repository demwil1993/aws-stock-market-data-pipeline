```
s3://<cloudformation-generated-stock-data-bucket>/
│
├── raw/
│   └── quotes/
│       └── year=2026/
│           └── month=07/
│               └── day=16/
│                   └── hour=14/
│                       └── quotes_20260716T140000Z.jsonl
│
├── standardized/
│   └── quotes/
│       └── year=2026/
│           └── month=07/
│               └── day=16/
│                   └── quotes_20260716T140000Z.jsonl
│
├── curated/
│   └── quotes/
│       └── year=2026/
│           └── month=07/
│               └── day=16/
│                   └── part-00000-<job-id>.snappy.parquet
│
├── rejected/
│   └── quotes/
│       └── year=2026/
│           └── month=07/
│               └── day=16/
│                   └── rejected-<job-id>.jsonl
│
├── athena-results/
│   └── stock-pipeline-workgroup/
│
└── glue-assets/
    └── scripts/
        └── stock_quote_transform.py
```