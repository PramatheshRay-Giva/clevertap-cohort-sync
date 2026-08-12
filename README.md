This code automates the cohort sync from metabase to clevertap

# 🔄 CleverTap Cohort Sync Automation

This repository contains an automated Python pipeline that extracts daily customer cohort data from Metabase and seamlessly uploads it to CleverTap as Custom List Segments. 

The script is fully automated using **GitHub Actions** and is scheduled to run every night at **2:00 AM IST**.

## ✨ Features
* **Fully Automated Scheduled Syncs:** Runs in the cloud via GitHub Actions without manual intervention.
* **Smart Naming Convention:** Automatically names segments in CleverTap with the current date (e.g., `12Aug26_A1-P1-New`) to keep the dashboard organized.
* **Auto-Retry Mechanism:** Built-in resilience that automatically waits and retries up to 3 times if there is a network drop from Metabase or CleverTap.
* **Data Formatting:** Cleans and formats raw phone numbers from Metabase into the strict `+91XXXXXXXXXX` structure required by CleverTap.
* **Execution Summary:** Outputs a clean summary at the end of every run detailing any cohorts that ultimately failed and need manual re-running.

## 🔐 Security & Secrets
Because this script handles sensitive customer data and API access, passwords are **never** hardcoded into the script. They are securely stored in GitHub Secrets.

To run this script, the following secrets must be configured in `Settings -> Secrets and variables -> Actions`:
* `MB_PASSWORD`: Your Metabase account password.
* `CT_PASSCODE`: Your CleverTap API Passcode.

## ⚙️ How It Works
1. **Authentication:** Connects to the Metabase API to generate a temporary session token.
2. **Data Extraction:** Loops through the predefined list of cohorts (`FILTERS_TO_PROCESS`) and downloads the CSV output for each.
3. **Transformation:** Uses `pandas` to drop empty rows and format the phone numbers.
4. **Upload:** Uses CleverTap's pre-signed S3 URL method to securely upload the CSV and create the segment.
5. **Cleanup:** Deletes the temporary CSV file before moving to the next cohort.

## 🚀 How to Run Manually
If you need to run the sync outside of its normal 2:00 AM schedule (or want to test a failed cohort):
1. Go to the **Actions** tab in this repository.
2. Click on **Nightly CleverTap Sync** on the left menu.
3. Click the **Run workflow** dropdown on the right side.
4. Click the green **Run workflow** button.

## 🛠️ How to Update the Cohort List
If you ever need to add new segments or remove old ones, simply edit the `main.py` file:
1. Locate the `FILTERS_TO_PROCESS` list near the top of the script.
2. Add or remove your exact filter names (e.g., `"New-Cohort-Name"`).
3. Commit the changes. The pipeline will automatically pick up the new list on its next run.
