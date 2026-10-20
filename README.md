# Meridian E-Portfolio (Streamlit)

This repository contains a beginner-friendly Streamlit e-portfolio with two sections:
1. **Problem** — charts pilot demand versus available capacity and estimated skill gaps.
2. **Solution Guide** — compares four staffing scenarios and estimates vendor costs by role.

The app reads the `Inputs` sheet from the provided Excel workbook and calculates the charts in Python. It does not rely on cached Excel formula results.

## Run on your computer

1. Install Python 3.10 or newer from https://www.python.org/downloads/
2. Extract this ZIP file.
3. Open the extracted folder.
4. Open Command Prompt/Terminal in that folder.
5. Install packages:

   ```bash
   pip install -r requirements.txt
   ```

6. Start the app:

   ```bash
   streamlit run app.py
   ```

A browser tab should open with the portfolio.

## Upload to GitHub

1. Sign in to GitHub and create a new repository.
2. Extract this ZIP on your computer.
3. Upload `app.py`, `requirements.txt`, this `README.md`, and the Excel workbook to the repository.
4. To publish it as a website, open Streamlit Community Cloud at https://share.streamlit.io/ and connect the GitHub repository.

## Important assumptions

- The charts use the workbook's `Inputs` sheet as the source for role data and assumptions.
- Scenario figures are conditional estimates, not management approvals.
- The calculations assume theoretical internal capacity is usable. Confirm named employee releases, existing-service cover, access, authority and onboarding before relying on the results.
- The workbook says the pilot is a four-week scope; do not extrapolate these figures to the whole 8,400-person centre.
