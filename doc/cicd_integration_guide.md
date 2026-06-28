# CI/CD Integration Guide: Petro Integration Module (Odoo v18)

Integrating automated tests into your CI/CD pipeline ensures that every code change is automatically verified before being deployed to production. This guide focuses on using **GitHub Actions**, the most common tool for Odoo development.

## 1. Pipeline Overview

The pipeline will perform the following steps on every **Pull Request** or **Push** to the `main` branch:
1.  **Checkout Code:** Pull the latest version of your Odoo module.
2.  **Setup Python:** Install the required Python version (3.12+ for Odoo v18).
3.  **Install Dependencies:** Install Odoo core, PostgreSQL, and module-specific requirements (`requests`).
4.  **Run Odoo Tests:** Execute the `petro_integration` test suite using `odoo-bin`.

## 2. GitHub Actions Workflow Template

Create a file at `.github/workflows/odoo_tests.yml` in your repository:

```yaml
name: Odoo v18 Tests

on:
  push:
    branches: [ main, 18.0 ]
  pull_request:
    branches: [ main, 18.0 ]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: odoo
          POSTGRES_PASSWORD: odoo_password
          POSTGRES_DB: postgres
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - name: Checkout Module
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install System Dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y python3-dev libxml2-dev libxslt1-dev libldap2-dev libsasl2-dev libpq-dev

      - name: Install Odoo & Requirements
        run: |
          pip install --upgrade pip
          pip install requests  # Module dependency
          # Install Odoo 18.0 (Example using pip, adjust to your Odoo source)
          pip install git+https://github.com/odoo/odoo.git@18.0#egg=odoo

      - name: Run Petro Integration Tests
        env:
          HOST: localhost
          USER: odoo
          PASSWORD: odoo_password
        run: |
          # Run Odoo tests for the specific module
          odoo -i petro_integration --test-enable --stop-after-init --database=test_db --log-level=test
```

## 3. Key CI/CD Best Practices

### 3.1. Secret Management
Never hardcode API keys or database passwords. Use **GitHub Secrets** (`Settings > Secrets and variables > Actions`) to store sensitive data and reference them in your workflow:
```yaml
env:
  PETRO_CLIENT_ID: ${{ secrets.PETRO_CLIENT_ID }}
```

### 3.2. Idempotency & Clean Database
Always run tests on a fresh database (`--database=test_db`). Odoo's `TransactionCase` (used in our scripts) automatically rolls back changes after each test, ensuring a clean state for the next run.

### 3.3. Linting and Code Quality
Add a step to check for Odoo coding standards using `pylint-odoo`:
```yaml
- name: Lint with Pylint Odoo
  run: |
    pip install pylint-odoo
    pylint --load-plugins=pylint_odoo petro_integration/
```

## 4. Integration with Odoo.sh
If you are using **Odoo.sh**, CI/CD is built-in. 
1.  Push your `petro_integration` module to your linked GitHub repository.
2.  Odoo.sh will automatically detect the module and run the tests in the `tests/` directory.
3.  Check the **Builds** tab in the Odoo.sh dashboard to see the test results.

---

*Prepared by **Manus AI** for the Petro Integration Project.*
