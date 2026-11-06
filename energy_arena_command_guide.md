# Energy Arena Forecasting & Submission Guide

This file contains the exact terminal commands required to generate local forecast payloads and submit them to the Energy Arena platform for **Challenge ID 2**.

## Prerequisites
Always ensure you are executing commands inside your project directory with your virtual environment activated, or by invoking the virtual environment's Python executable directly.

---

## 1. Generate Local Forecast Payload
To generate predictions for an upcoming target date and save them to `test_payload.json`, use the following command:

```bash
.venv\Scripts\python run_forecast_model.py --target_date 03-11-2026 --challenge_id 2 --save_payload test_payload.json
```

* **Parameters:**
  * `--target_date`: The target date for your forecast (format `DD-MM-YYYY`).
  * `--challenge_id`: Must be set to `2` for DE_LU Day-Ahead Prices point forecasts.
  * `--save_payload`: Specifies the filename where the JSON payload will be written.

---

## 2. Submit Forecast to Energy Arena
Once your payload has been generated successfully and inspected, push your submission to the platform with this command:

```bash
.venv\Scripts\python submit_forecast_to_energy_arena.py --payload test_payload.json
```

* **Verification:** A successful submission will return an `OK -> submission_id=XXXXX` confirmation.

---

## 3. Check Open Challenges & Deadlines
To view all active challenges, target windows, and submission deadlines, run:

```bash
.venv\Scripts\python run_forecast_model.py --list_open_challenges
```