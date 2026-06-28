# Odoo v18 Integration Plan: Petro Integration API

This document outlines the plan for integrating the Petro Integration API with Odoo v18.

## 1. API Analysis

The provided API specification is a Postman collection, which describes the available endpoints, authentication method, and basic request structures. 

### 1.1. Authentication

The API uses a client ID and client secret passed as headers for authentication:

- `client-id`: `{{ClientId}}`
- `client-secret`: `{{ClientSecret}}`

These credentials will need to be securely stored in Odoo's configuration.

### 1.2. API Endpoints

The following API endpoints are available:

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/SalesTransaction/List` | Retrieves a list of sales transactions within a specified date range. |
| GET | `/api/TankMeasurement` | Fetches tank measurement data for a given date range. |
| GET | `/api/BusinessDates/ListShifts` | Lists available shifts. |
| GET | `/api/BusinessDates/EndOfShiftReport` | Generates an end-of-shift report for a specific shift ID. |

### 1.3. Data Structures

The API responses are in JSON format. The exact structure of the data returned from each endpoint is not yet known, as the `response` field in the Postman collection is empty. This will need to be determined by making test calls to the API.

## 2. Odoo Integration Architecture

To integrate this API with Odoo, we will create a custom Odoo module. This module will handle the following:

- **Configuration:** Store the API credentials and other settings.
- **API Connection:** A centralized service to handle requests to the Petro Integration API.
- **Data Models:** Odoo models to store the data retrieved from the API.
- **Scheduled Jobs:** Automated tasks to periodically fetch data from the API.
- **User Interface:** Views and menus to display the integrated data within Odoo.

This initial analysis and design will be refined as we proceed with the implementation.

## 3. Odoo v18 Module Structure and Base Configuration

We will create a new Odoo module named `petro_integration`. The basic structure will include:

```
petro_integration/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   └── petro_config.py
│   └── petro_sales_transaction.py
│   └── petro_tank_measurement.py
│   └── petro_shift.py
├── views/
│   ├── petro_config_views.xml
│   ├── petro_sales_transaction_views.xml
│   ├── petro_tank_measurement_views.xml
│   └── petro_shift_views.xml
├── security/
│   └── ir.model.access.csv
├── wizards/
│   └── __init__.py
│   └── petro_sync_wizard.py
├── data/
│   └── ir_cron_data.xml
└── controllers/
    └── __init__.py
    └── main.py
```

### 3.1. `__manifest__.py`

This file will define the module's metadata.

```python
{
    'name': 'Petro Integration',
    'version': '1.0',
    'category': 'Integrations',
    'summary': 'Integrates Odoo with the Petro Integration API',
    'author': 'Manus AI',
    ''website': 'https://www.manus.im',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/petro_config_views.xml',
        'views/petro_sales_transaction_views.xml',
        'views/petro_tank_measurement_views.xml',
        'views/petro_shift_views.xml',
        'data/ir_cron_data.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
```

### 3.2. `petro_config.py` (models)

This model will store the API credentials and other configuration settings.

```python
from odoo import fields, models

class PetroConfig(models.Model):
    _name = 'petro.config'
    _description = 'Petro Integration Configuration'

    api_url = fields.Char(string='API URL', required=True, default='https://petrointegrationapi.cashin.sa')
    client_id = fields.Char(string='Client ID', required=True, groups='base.group_system')
    client_secret = fields.Char(string='Client Secret', required=True, groups='base.group_system')
```

### 3.3. `petro_config_views.xml` (views)

This file will define the view for the Petro Integration Configuration.

```xml
<odoo>
    <record id="petro_config_form_view" model="ir.ui.view">
        <field name="name">petro.config.form</field>
        <field name="model">petro.config</field>
        <field name="arch" type="xml">
            <form string="Petro Integration Configuration">
                <sheet>
                    <group>
                        <field name="api_url"/>
                        <field name="client_id" password="True"/>
                        <field name="client_secret" password="True"/>
                    </group>
                </sheet>
            </form>
        </field>
    </record>

    <record id="petro_config_action" model="ir.actions.act_window">
        <field name="name">Petro Integration Configuration</field>
        <field name="res_model">petro.config</field>
        <field name="view_mode">form</field>
        <field name="target">inline</field>
    </record>

    <menuitem id="petro_integration_menu_root" name="Petro Integration" sequence="100" web_icon="fa fa-plug"/>
    <menuitem id="petro_integration_config_menu" name="Configuration" parent="petro_integration_menu_root" action="petro_config_action" sequence="10"/>
</odoo>
```

This structure provides the foundation for the Odoo module, allowing for configuration of the API credentials and setting up the basic menu items.

## 4. Implement API Connection and Data Fetching Logic

To interact with the Petro Integration API, we will create a dedicated service layer within our Odoo module. This service will handle authentication, construct API requests, and process responses. We will extend the `petro.config` model to include methods for fetching data from the various API endpoints.

### 4.1. `petro_config.py` (API Connection Methods)

We will add methods to the `PetroConfig` model to handle API calls. This will involve using the `requests` library, which is a standard Python library for making HTTP requests. If not already installed in the Odoo environment, it can be installed via `pip`.

```python
import requests
import json
from odoo import fields, models, _
from odoo.exceptions import UserError

class PetroConfig(models.Model):
    _name = 'petro.config'
    _description = 'Petro Integration Configuration'

    api_url = fields.Char(string='API URL', required=True, default='https://petrointegrationapi.cashin.sa')
    client_id = fields.Char(string='Client ID', required=True, groups='base.group_system')
    client_secret = fields.Char(string='Client Secret', required=True, groups='base.group_system')

    def _get_api_headers(self):
        self.ensure_one()
        return {
            'client-id': self.client_id,
            'client-secret': self.client_secret,
            'Content-Type': 'application/json',
        }

    def _call_api(self, endpoint, params=None, method='GET'):
        self.ensure_one()
        url = f"{self.api_url}{endpoint}"
        headers = self._get_api_headers()
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=10)
            elif method == 'POST':
                response = requests.post(url, headers=headers, json=params, timeout=10)
            else:
                raise UserError(_('Unsupported API method: %s', method))

            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            return response.json()
        except requests.exceptions.HTTPError as errh:
            raise UserError(_("HTTP Error: %s", errh))
        except requests.exceptions.ConnectionError as errc:
            raise UserError(_("Error Connecting: %s", errc))
        except requests.exceptions.Timeout as errt:
            raise UserError(_("Timeout Error: %s", errt))
        except requests.exceptions.RequestException as err:
            raise UserError(_("Something went wrong: %s", err))
        except json.JSONDecodeError:
            raise UserError(_("Failed to decode JSON response from API."))

    def get_sales_transactions(self, from_date, to_date, page_size=100, page_number=1):
        self.ensure_one()
        endpoint = "/api/SalesTransaction/List"
        params = {
            'fromDate': from_date.strftime('%Y-%m-%d %H:%M:%S'),
            'toDate': to_date.strftime('%Y-%m-%d %H:%M:%S'),
            'pageSize': page_size,
            'pageNumber': page_number,
        }
        return self._call_api(endpoint, params=params, method='GET')

    def get_tank_measurements(self, date_from, date_to, page_size=1000):
        self.ensure_one()
        endpoint = "/api/TankMeasurement"
        params = {
            'DateFrom': date_from.strftime('%Y-%m-%d'),
            'DateTo': date_to.strftime('%Y-%m-%d'),
            'PageSize': page_size,
        }
        return self._call_api(endpoint, params=params, method='GET')

    def get_shifts_list(self):
        self.ensure_one()
        endpoint = "/api/BusinessDates/ListShifts"
        return self._call_api(endpoint, method='GET')

    def get_end_of_shift_report(self, shift_id):
        self.ensure_one()
        endpoint = "/api/BusinessDates/EndOfShiftReport"
        params = {
            'shiftId': shift_id,
        }
        return self._call_api(endpoint, params=params, method='GET')
```

### 4.2. Installation of `requests` Library

Before running the Odoo module, ensure the `requests` library is installed in the Odoo environment. This can typically be done via:

```bash
sudo pip3 install requests
```

These methods provide a robust way to interact with the Petro Integration API, handling authentication and error management. The next step will involve defining Odoo models to store the fetched data and implementing the data mapping and synchronization logic.

## 5. Develop Data Mapping and Synchronization Logic for Odoo Models

This section outlines the Odoo models required to store the data fetched from the Petro Integration API and the logic for mapping API responses to these models. For each API endpoint, we will define a corresponding Odoo model.

### 5.1. `petro_sales_transaction.py` (models)

This model will store sales transaction data.

```python
from odoo import fields, models

class PetroSalesTransaction(models.Model):
    _name = 'petro.sales.transaction'
    _description = 'Petro Sales Transaction'

    # Example fields - these will need to be adjusted based on actual API response
    transaction_id = fields.Char(string='Transaction ID', required=True, index=True, copy=False)
    transaction_date = fields.Datetime(string='Transaction Date')
    amount = fields.Float(string='Amount')
    product_name = fields.Char(string='Product Name')
    # Add more fields as per API response for Sales Transactions

    _sql_constraints = [
        ('transaction_id_unique', 'unique(transaction_id)', 'Transaction ID must be unique!'),
    ]

    def _sync_sales_transactions(self, transactions_data):
        for transaction in transactions_data:
            # Map API data to Odoo fields
            vals = {
                'transaction_id': transaction.get('Id'), # Assuming 'Id' is the unique identifier from API
                'transaction_date': transaction.get('TransactionDateTime'),
                'amount': transaction.get('TotalAmount'),
                'product_name': transaction.get('ProductName'),
                # Map other fields
            }
            # Create or update record
            self.search([('transaction_id', '=', vals['transaction_id'])], limit=1).write(vals) or self.create(vals)
```

### 5.2. `petro_tank_measurement.py` (models)

This model will store tank measurement data.

```python
from odoo import fields, models

class PetroTankMeasurement(models.Model):
    _name = 'petro.tank.measurement'
    _description = 'Petro Tank Measurement'

    # Example fields - these will need to be adjusted based on actual API response
    measurement_id = fields.Char(string='Measurement ID', required=True, index=True, copy=False)
    measurement_date = fields.Date(string='Measurement Date')
    tank_id = fields.Char(string='Tank ID')
    volume = fields.Float(string='Volume')
    # Add more fields as per API response for Tank Measurements

    _sql_constraints = [
        ('measurement_id_unique', 'unique(measurement_id)', 'Measurement ID must be unique!'),
    ]

    def _sync_tank_measurements(self, measurements_data):
        for measurement in measurements_data:
            vals = {
                'measurement_id': measurement.get('Id'),
                'measurement_date': measurement.get('Date'),
                'tank_id': measurement.get('TankIdentifier'),
                'volume': measurement.get('CurrentVolume'),
                # Map other fields
            }
            self.search([('measurement_id', '=', vals['measurement_id'])], limit=1).write(vals) or self.create(vals)
```

### 5.3. `petro_shift.py` (models)

This model will store shift information.

```python
from odoo import fields, models

class PetroShift(models.Model):
    _name = 'petro.shift'
    _description = 'Petro Shift'

    # Example fields - these will need to be adjusted based on actual API response
    shift_id = fields.Char(string='Shift ID', required=True, index=True, copy=False)
    shift_name = fields.Char(string='Shift Name')
    start_datetime = fields.Datetime(string='Start Datetime')
    end_datetime = fields.Datetime(string='End Datetime')
    # Add more fields as per API response for Shifts

    _sql_constraints = [
        ('shift_id_unique', 'unique(shift_id)', 'Shift ID must be unique!'),
    ]

    def _sync_shifts(self, shifts_data):
        for shift in shifts_data:
            vals = {
                'shift_id': shift.get('Id'),
                'shift_name': shift.get('Name'),
                'start_datetime': shift.get('StartDateTime'),
                'end_datetime': shift.get('EndDateTime'),
                # Map other fields
            }
            self.search([('shift_id', '=', vals['shift_id'])], limit=1).write(vals) or self.create(vals)
```

### 5.4. `ir.model.access.csv` (security)

This file will define access rights for the new models.

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_petro_config,petro.config.access,model_petro_config,base.group_system,1,1,1,1
access_petro_sales_transaction,petro.sales.transaction.access,model_petro_sales_transaction,base.group_user,1,0,0,0
access_petro_tank_measurement,petro.tank.measurement.access,model_petro_tank_measurement,base.group_user,1,0,0,0
access_petro_shift,petro.shift.access,model_petro_shift,base.group_user,1,0,0,0
```

### 5.5. `ir_cron_data.xml` (data)

This file will define scheduled actions to fetch data periodically.

```xml
<odoo>
    <data noupdate="1">
        <record id="ir_cron_sync_sales_transactions" model="ir.cron">
            <field name="name">Petro: Sync Sales Transactions</field>
            <field name="model_id" ref="model_petro_config"/>
            <field name="state">code</field>
            <field name="code">model.browse(1).get_sales_transactions_and_sync()</field>
            <field name="interval_number">1</field>
            <field name="interval_type">hours</field>
            <field name="numbercall">-1</field>
            <field name="doall">False</field>
        </record>
        <record id="ir_cron_sync_tank_measurements" model="ir.cron">
            <field name="name">Petro: Sync Tank Measurements</field>
            <field name="model_id" ref="model_petro_config"/>
            <field name="state">code</field>
            <field name="code">model.browse(1).get_tank_measurements_and_sync()</field>
            <field name="interval_number">1</field>
            <field name="interval_type">days</field>
            <field name="numbercall">-1</field>
            <field name="doall">False</field>
        </record>
        <record id="ir_cron_sync_shifts" model="ir.cron">
            <field name="name">Petro: Sync Shifts</field>
            <field name="model_id" ref="model_petro_config"/>
            <field name="state">code</field>
            <field name="code">model.browse(1).get_shifts_list_and_sync()</field>
            <field name="interval_number">1</field>
            <field name="interval_type">days</field>
            <field name="numbercall">-1</field>
            <field name="doall">False</field>
        </record>
    </data>
</odoo>
```

**Note:** The `get_sales_transactions_and_sync()`, `get_tank_measurements_and_sync()`, and `get_shifts_list_and_sync()` methods will need to be added to the `petro.config` model to orchestrate the fetching and synchronization of data. These methods will call the API fetching methods and then the `_sync_` methods on the respective data models.

This section provides the core logic for storing and synchronizing data from the Petro Integration API into Odoo. The next phase will involve delivering the complete integration guide and code to the user.

### 5.6. Orchestration Methods in `petro_config.py`

To orchestrate the data fetching and synchronization, we will add the following methods to the `PetroConfig` model. These methods will be called by the scheduled actions defined in `ir_cron_data.xml`.

```python
# ... (previous code in petro_config.py)

    def get_sales_transactions_and_sync(self):
        self.ensure_one()
        # Define date range for fetching sales transactions
        # For initial sync, you might fetch a larger historical range
        # For recurring sync, fetch data since the last successful sync
        to_date = fields.Datetime.now()
        from_date = to_date - timedelta(days=1) # Fetch data for the last day

        sales_transactions = self.get_sales_transactions(from_date, to_date)
        if sales_transactions:
            self.env["petro.sales.transaction"]._sync_sales_transactions(sales_transactions)

    def get_tank_measurements_and_sync(self):
        self.ensure_one()
        to_date = fields.Date.today()
        from_date = to_date - timedelta(days=1) # Fetch data for the last day

        tank_measurements = self.get_tank_measurements(from_date, to_date)
        if tank_measurements:
            self.env["petro.tank.measurement"]._sync_tank_measurements(tank_measurements)

    def get_shifts_list_and_sync(self):
        self.ensure_one()
        shifts = self.get_shifts_list()
        if shifts:
            self.env["petro.shift"]._sync_shifts(shifts)

# ... (rest of the code in petro_config.py)
```

**Note:** You will need to import `timedelta` from the `datetime` module at the beginning of `petro_config.py`:

```python
from datetime import timedelta
```

This completes the core logic for the Odoo module. The next step is to deliver the complete integration guide and code to the user.
