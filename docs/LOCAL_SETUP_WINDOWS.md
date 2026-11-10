# Local setup on Windows (VS Code)

This guide assumes you opened the repository root folder, `arshiataheri851-ops-main`, in VS Code. It uses one virtual environment at the repository root and does **not** require PowerShell script activation.

## 1. Create the virtual environment

Run these commands in the VS Code PowerShell terminal from the repository root:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
```

If `.venv` already exists, do not create it again. Continue with the next step.

## 2. Install the API and development tools

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".\projects\persian-sentiment-api[dev]"
```

## 3. Run the tests

```powershell
.\.venv\Scripts\python.exe -m pytest .\projects\persian-sentiment-api\tests -q
```

The tests use a fake predictor; they do not download model weights.

## 4. Start the API

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir .\projects\persian-sentiment-api --reload
```

Then open http://127.0.0.1:8000/docs.

## 5. Enable real model inference

Only when you are ready to download the pretrained model dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".\projects\persian-sentiment-api[inference]"
```

The model files are downloaded from Hugging Face on the first prediction. Keep the API running and send a Persian review through `POST /v1/sentiment`.

## Why these commands avoid the PowerShell activation error

PowerShell may block `Activate.ps1` due to the machine's execution policy. You do not need to weaken that policy. Calling `.venv\Scripts\python.exe` directly runs the interpreter inside the virtual environment without activating a script.

## If installation fails

Do not repeatedly retry different commands. Copy the **first complete error block** from the terminal; the final summary line alone is not enough to identify the cause.
