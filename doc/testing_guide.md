# Testing Guide: Petro Integration Module for Odoo v18

This guide provides step-by-step instructions to verify the installation and functionality of the `petro_integration` module.

## Prerequisites

Before you begin, ensure the following:

- The `petro_integration` module is installed in your Odoo v18 instance.
- The `requests` Python library is installed in your Odoo environment:
  ```bash
  sudo pip3 install requests
  ```
- You have the API credentials: `client-id` and `client-secret`.

---

## Step 1: Configure API Credentials

The first step is to set up the connection between Odoo and the Petro Integration API.

1.  Log in to Odoo as an Administrator.
2.  Navigate to the **Petro Integration** menu.
3.  Go to **Configuration** > **Petro Integration Configuration**.
4.  Create a new record and enter the following details:
    - **API URL:** `https://petrointegrationapi.cashin.sa`
    - **Client ID:** Your provided Client ID.
    - **Client Secret:** Your provided Client Secret.
5.  Click **Save**.

---

## Step 2: Perform Manual Synchronization

To verify the API connection and data mapping, perform a manual sync.

1.  On the **Petro Integration Configuration** form, you will see three buttons in the header:
    - **Sync Sales:** Fetches sales transactions from the last 24 hours.
    - **Sync Tanks:** Fetches tank measurements from the last 24 hours.
    - **Sync Shifts:** Fetches the list of shifts.
2.  Click **Sync Sales**. If the sync is successful, no error message will appear.
3.  Click **Sync Tanks** and **Sync Shifts** to verify those connections as well.

---

## Step 3: Verify Synchronized Data

Check the respective menus to ensure the data has been correctly imported into Odoo.

1.  Navigate to **Petro Integration** > **Sales Transactions**. Verify that the list contains transactions from the API.
2.  Navigate to **Petro Integration** > **Tank Measurements**. Verify that the tank data is present.
3.  Navigate to **Petro Integration** > **Shifts**. Verify that the shift information is correctly listed.

---

## Step 4: Verify Scheduled Actions (Automation)

The module includes scheduled actions to automate data fetching.

1.  Enable **Developer Mode** in Odoo.
2.  Navigate to **Settings** > **Technical** > **Automation** > **Scheduled Actions**.
3.  Search for actions starting with **Petro:**:
    - `Petro: Sync Sales Transactions` (Runs every hour)
    - `Petro: Sync Tank Measurements` (Runs every day)
    - `Petro: Sync Shifts` (Runs every day)
4.  Open any of these actions and click **Run Manually** to test the automation logic.
5.  Check the **Execution Timeline** or logs to ensure they complete without errors.

---

## Troubleshooting

- **Connection Error:** Ensure your Odoo server has internet access and can reach `https://petrointegrationapi.cashin.sa`.
- **Authentication Error:** Double-check your `client-id` and `client-secret`.
- **No Data Imported:** Verify the date range in the API calls. The default sync fetches data from the last 24 hours. If there are no transactions in that period, no data will be imported.
- **Odoo Logs:** Check the Odoo server logs for detailed error messages if a sync fails.
